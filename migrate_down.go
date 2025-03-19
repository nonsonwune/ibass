package main

import (
	"bytes"
	"context"
	"database/sql"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"sync"
	"time"

	_ "github.com/lib/pq"
)

const (
	sourceDBURL = "postgresql://nuf_user:Af8YQayi2G1WKrPcs46efJbFZj5csXGo@dpg-ctf6pkjtq21c73brp4og-a.oregon-postgres.render.com/nuf_render_db?sslmode=require"
	targetDBURL = "postgresql://nonsonwune:password@localhost:5432/university_courses?sslmode=disable"
	maxWorkers  = 4 // Reduced to avoid overwhelming connections
)

type Table struct {
	Name         string
	Dependencies map[string]bool
}

type Wave struct {
	Tables []string
	Number int
}

// Create a buffered channel to limit concurrent executions
var semaphore = make(chan struct{}, maxWorkers)

func getDependencies(db *sql.DB) (map[string]*Table, error) {
	tables := make(map[string]*Table)

	// Get all tables excluding backup tables
	rows, err := db.Query(`
		SELECT table_name 
		FROM information_schema.tables 
		WHERE table_schema = 'public' 
		AND table_type = 'BASE TABLE'
		AND table_name NOT LIKE '%backup%'
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	// Initialize tables map
	for rows.Next() {
		var tableName string
		if err := rows.Scan(&tableName); err != nil {
			return nil, err
		}
		tables[tableName] = &Table{
			Name:         tableName,
			Dependencies: make(map[string]bool),
		}
	}

	// Get foreign key relationships
	for tableName := range tables {
		rows, err := db.Query(`
			SELECT DISTINCT ccu.table_name AS foreign_table_name
			FROM information_schema.table_constraints AS tc
			JOIN information_schema.constraint_column_usage AS ccu
			ON ccu.constraint_name = tc.constraint_name
			WHERE tc.constraint_type = 'FOREIGN KEY'
			AND tc.table_name = $1
		`, tableName)
		if err != nil {
			return nil, err
		}

		for rows.Next() {
			var foreignTable string
			if err := rows.Scan(&foreignTable); err != nil {
				rows.Close()
				return nil, err
			}
			if _, exists := tables[foreignTable]; exists {
				tables[tableName].Dependencies[foreignTable] = true
			}
		}
		rows.Close()
	}

	return tables, nil
}

func groupTablesIntoWaves(tables map[string]*Table) []Wave {
	var waves []Wave
	remainingTables := make(map[string]bool)
	for tableName := range tables {
		remainingTables[tableName] = true
	}

	waveNum := 1
	for len(remainingTables) > 0 {
		var currentWave []string

		for tableName := range remainingTables {
			hasDependency := false
			for depTable := range tables[tableName].Dependencies {
				if remainingTables[depTable] {
					hasDependency = true
					break
				}
			}

			if !hasDependency {
				currentWave = append(currentWave, tableName)
			}
		}

		// Handle potential circular dependencies
		if len(currentWave) == 0 {
			// Just take one table to break the cycle
			for tableName := range remainingTables {
				currentWave = append(currentWave, tableName)
				break
			}
		}

		// Remove migrated tables from remaining
		for _, tableName := range currentWave {
			delete(remainingTables, tableName)
		}

		waves = append(waves, Wave{Tables: currentWave, Number: waveNum})
		waveNum++
	}

	return waves
}

func migrateTable(ctx context.Context, table string, waveNum int, wg *sync.WaitGroup, errChan chan<- error) {
	defer wg.Done()

	// Acquire semaphore
	semaphore <- struct{}{}
	defer func() { <-semaphore }()

	log.Printf("Starting migration for table %s (Wave %d)", table, waveNum)

	// Create temporary directory
	tempDir, err := os.MkdirTemp("", "dbmigration")
	if err != nil {
		errChan <- fmt.Errorf("failed to create temp dir for table %s: %v", table, err)
		return
	}
	defer os.RemoveAll(tempDir)

	dumpFile := filepath.Join(tempDir, fmt.Sprintf("%s_dump.sql", table))

	// Capture stdout and stderr
	var stdout, stderr bytes.Buffer

	// Dump table
	dumpCmd := exec.CommandContext(ctx, "pg_dump",
		sourceDBURL,
		"-t", fmt.Sprintf("public.%s", table),
		"--clean",
		"--if-exists",
		"--no-owner",
		"--no-privileges",
		"-f", dumpFile,
	)
	dumpCmd.Stdout = &stdout
	dumpCmd.Stderr = &stderr

	if err := dumpCmd.Run(); err != nil {
		errChan <- fmt.Errorf("failed to dump table %s: %v\nStdout: %s\nStderr: %s",
			table, err, stdout.String(), stderr.String())
		return
	}

	// Verify dump file exists and has content
	fileInfo, err := os.Stat(dumpFile)
	if err != nil {
		errChan <- fmt.Errorf("dump file for %s not found: %v", table, err)
		return
	}

	if fileInfo.Size() == 0 {
		errChan <- fmt.Errorf("dump file for %s is empty", table)
		return
	}

	// Reset buffers
	stdout.Reset()
	stderr.Reset()

	// Import table
	importCmd := exec.CommandContext(ctx, "psql", targetDBURL, "-f", dumpFile)
	importCmd.Stdout = &stdout
	importCmd.Stderr = &stderr

	if err := importCmd.Run(); err != nil {
		errChan <- fmt.Errorf("failed to import table %s: %v\nStdout: %s\nStderr: %s",
			table, err, stdout.String(), stderr.String())
		return
	}

	log.Printf("Successfully migrated table %s (Wave %d)", table, waveNum)
}

// Function to test if a table exists
func tableExists(db *sql.DB, tableName string) (bool, error) {
	var exists bool
	query := `
		SELECT EXISTS (
			SELECT FROM information_schema.tables 
			WHERE table_schema = 'public' 
			AND table_name = $1
		)
	`
	err := db.QueryRow(query, tableName).Scan(&exists)
	return exists, err
}

// Function to list all tables in the database
func listTables(db *sql.DB) ([]string, error) {
	rows, err := db.Query(`
		SELECT table_name 
		FROM information_schema.tables 
		WHERE table_schema = 'public' 
		AND table_type = 'BASE TABLE'
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var tables []string
	for rows.Next() {
		var tableName string
		if err := rows.Scan(&tableName); err != nil {
			return nil, err
		}
		tables = append(tables, tableName)
	}
	return tables, nil
}

func main() {
	start := time.Now()
	log.Println("Starting parallel database migration...")

	// Connect to source database
	log.Println("Connecting to source database...")
	sourceDB, err := sql.Open("postgres", sourceDBURL)
	if err != nil {
		log.Fatalf("Failed to connect to source database: %v", err)
	}
	defer sourceDB.Close()

	// Test connection
	err = sourceDB.Ping()
	if err != nil {
		log.Fatalf("Failed to ping source database: %v", err)
	}
	log.Println("Successfully connected to source database")

	// List all tables in source database
	tables, err := listTables(sourceDB)
	if err != nil {
		log.Fatalf("Failed to list tables: %v", err)
	}
	log.Printf("Found %d tables in source database", len(tables))

	// Connect to target database to verify it exists
	log.Println("Connecting to target database...")
	targetDB, err := sql.Open("postgres", targetDBURL)
	if err != nil {
		log.Fatalf("Failed to connect to target database: %v", err)
	}
	defer targetDB.Close()

	err = targetDB.Ping()
	if err != nil {
		log.Fatalf("Failed to ping target database: %v", err)
	}
	log.Println("Successfully connected to target database")

	// Get table dependencies
	tableStructs, err := getDependencies(sourceDB)
	if err != nil {
		log.Fatalf("Failed to get table dependencies: %v", err)
	}

	// Group tables into waves
	waves := groupTablesIntoWaves(tableStructs)
	log.Printf("Grouped tables into %d waves", len(waves))

	ctx := context.Background()
	var failed bool

	// Process each wave
	for _, wave := range waves {
		log.Printf("Processing wave %d with %d tables", wave.Number, len(wave.Tables))

		var wg sync.WaitGroup
		errChan := make(chan error, len(wave.Tables))

		// Start migration for each table in the wave
		for _, table := range wave.Tables {
			wg.Add(1)
			go migrateTable(ctx, table, wave.Number, &wg, errChan)
			// Add slight delay to avoid overwhelming connections
			time.Sleep(100 * time.Millisecond)
		}

		// Wait for all tables in wave to complete
		wgDone := make(chan struct{})
		go func() {
			wg.Wait()
			close(wgDone)
		}()

		// Wait for either all tables to complete or an error to occur
		select {
		case <-wgDone:
			close(errChan)
			// Check for errors
			for err := range errChan {
				if err != nil {
					log.Printf("Error: %v", err)
					failed = true
				}
			}
		case <-time.After(15 * time.Minute):
			log.Printf("Wave %d timed out after 15 minutes", wave.Number)
			failed = true
		}

		if failed {
			log.Fatal("Migration failed")
		}
	}

	duration := time.Since(start)
	log.Printf("Migration completed successfully in %.2f seconds", duration.Seconds())
}
