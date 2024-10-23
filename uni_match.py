import pandas as pd
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import re
from datetime import datetime

def standardize_state_names(name):
    """Standardize state names in university names"""
    state_mappings = {
        "FCT, ABUJA": "ABUJA",
        "FCT ABUJA": "ABUJA",
        "ABUJA FCT": "ABUJA"
    }
    for old, new in state_mappings.items():
        name = name.replace(old, new)
    return name

def clean_university_name(name):
    """Clean university names while preserving important identifiers"""
    name = str(name).upper().strip()
    
    # Standardize state names
    name = standardize_state_names(name)
    
    # Remove program types and affiliations
    removals = [
        r'E LEARNING UNIVERSITIES OF NIGERIA$',
        r'AFFILIATED TO.*$',
        r'AFFL TO.*$',
        r'AFF TO.*$',
        r'DEGREE$',
    ]
    
    for pattern in removals:
        name = re.sub(pattern, '', name)
    
    # Remove state suffix if it exists
    name = re.sub(r'\s+[A-Z]+\s+STATE$', '', name)
    
    # Standardize common abbreviations
    replacements = {
        'TECH.': 'TECHNOLOGY',
        'TECH ': 'TECHNOLOGY ',
        'AGR.': 'AGRICULTURE',
        'AGRIC.': 'AGRICULTURE',
        'INT\'L': 'INTERNATIONAL',
        'ST.': 'SAINT',
        ' OF TECHNOLOGY': ' TECHNOLOGY',
        ' OF SCIENCE': ' SCIENCE',
        ' OF EDUCATION': ' EDUCATION'
    }
    
    for old, new in replacements.items():
        name = name.replace(old, new)
    
    # Remove extra whitespace
    name = ' '.join(name.split())
    
    return name.strip()

class UniversityMatcher:
    def __init__(self, universities_file, unis_file):
        """Initialize the matcher with the two input files"""
        self.universities_df = pd.read_csv(universities_file)
        self.unis_df = pd.read_csv(unis_file)
        
        # Convert column names to lowercase for consistency
        self.universities_df.columns = self.universities_df.columns.str.lower()
        self.unis_df.columns = self.unis_df.columns.str.lower()
        
        # Initialize matching dictionaries
        self.matches = {}
        self.match_scores = {}
        self.unmatched = []
        
        # Initialize report content
        self.report_content = []
        self.add_to_report(f"University Matching Report")
        self.add_to_report(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.add_to_report(f"\nInput Files:")
        self.add_to_report(f"Universities file: {universities_file}")
        self.add_to_report(f"Unis file: {unis_file}")
        self.add_to_report(f"\nColumns in universities file: {self.universities_df.columns.tolist()}")
        self.add_to_report(f"Columns in unis file: {self.unis_df.columns.tolist()}")
        self.add_to_report("\nMatching threshold set to 70%")
    
    def add_to_report(self, text):
        """Add text to report content and print to console"""
        self.report_content.append(text)
        print(text)
    
    def calculate_similarity(self, name1, name2):
        """Calculate similarity between two university names using multiple metrics"""
        # Basic token sort ratio
        token_sort = fuzz.token_sort_ratio(name1, name2)
        
        # Partial ratio to catch substring matches
        partial = fuzz.partial_ratio(name1, name2)
        
        # Token set ratio to handle word rearrangement and extra words
        token_set = fuzz.token_set_ratio(name1, name2)
        
        # Calculate weighted average
        return (token_sort * 0.4 + partial * 0.3 + token_set * 0.3)

    def find_best_match(self, name):
        """Find best match for a university name with minimum 70% similarity"""
        best_match = None
        best_score = 0
        
        for idx, row in self.unis_df.iterrows():
            score = self.calculate_similarity(name, row['clean_name'])
            if score > best_score and score >= 70:  # Enforce 70% minimum threshold
                best_score = score
                best_match = row
        
        return (best_match, best_score) if best_match is not None else None
    
    def process_matches(self):
        """Process matches with 70% minimum threshold"""
        self.add_to_report("\nCleaning university names...")
        self.universities_df['clean_name'] = self.universities_df['university_name'].apply(clean_university_name)
        self.unis_df['clean_name'] = self.unis_df['universities'].apply(clean_university_name)
        
        self.add_to_report("\nProcessing matches...")
        total = len(self.universities_df)
        
        for idx, row in self.universities_df.iterrows():
            if idx % 10 == 0:
                self.add_to_report(f"Processing {idx}/{total} universities...")
                
            result = self.find_best_match(row['clean_name'])
            
            if result:
                matched_row, score = result
                self.matches[row['clean_name']] = matched_row['clean_name']
                self.match_scores[row['clean_name']] = score
            else:
                self.unmatched.append(row['university_name'])
    
    def update_universities(self):
        """Update universities dataframe with matched data"""
        # Ensure the columns exist
        if 'website' not in self.universities_df.columns:
            self.universities_df['website'] = None
        if 'established' not in self.universities_df.columns:
            self.universities_df['established'] = None
        
        for idx, row in self.universities_df.iterrows():
            clean_name = row['clean_name']
            if clean_name in self.matches:
                matched_row = self.unis_df[self.unis_df['clean_name'] == self.matches[clean_name]].iloc[0]
                if 'website' in matched_row:
                    self.universities_df.at[idx, 'website'] = matched_row['website']
                if 'established' in matched_row:
                    self.universities_df.at[idx, 'established'] = matched_row['established']
    
    def generate_report(self):
        """Generate detailed matching report"""
        self.add_to_report("\nMatching Results:")
        self.add_to_report("-" * 80)
        
        self.add_to_report("\nSuccessful Matches (>= 70% similarity):")
        successful_matches = [(original, clean_name) for original, clean_name 
                            in zip(self.universities_df['university_name'], self.universities_df['clean_name'])
                            if clean_name in self.matches]
        
        for original, clean_name in successful_matches:
            matched_row = self.unis_df[self.unis_df['clean_name'] == self.matches[clean_name]].iloc[0]
            self.add_to_report(f"\nOriginal:    {original}")
            self.add_to_report(f"Cleaned:     {clean_name}")
            self.add_to_report(f"Matched to:  {matched_row['universities']}")
            self.add_to_report(f"Score:       {self.match_scores[clean_name]:.2f}%")
            if 'website' in matched_row:
                self.add_to_report(f"Website:     {matched_row['website']}")
            if 'established' in matched_row:
                self.add_to_report(f"Est. Year:   {matched_row['established']}")
        
        self.add_to_report(f"\nTotal Successful Matches: {len(successful_matches)}")
        
        self.add_to_report("\nUnmatched Universities (< 70% similarity):")
        for unmatched_uni in self.unmatched:
            self.add_to_report(f"- {unmatched_uni}")
        
        self.add_to_report(f"\nTotal Unmatched: {len(self.unmatched)}")
        
        match_rate = (len(successful_matches) / len(self.universities_df)) * 100
        self.add_to_report(f"\nOverall Match Rate: {match_rate:.2f}%")
    
    def save_results(self, output_file='universities_updated.csv', report_file='matching_report.txt'):
        """Save updated universities data and matching report"""
        # Save updated universities data
        output_df = self.universities_df.copy()
        if 'clean_name' in output_df.columns:
            output_df = output_df.drop('clean_name', axis=1)
        output_df.to_csv(output_file, index=False)
        self.add_to_report(f"\nUpdated universities data saved to: {output_file}")
        
        # Save report
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.report_content))
        self.add_to_report(f"Matching report saved to: {report_file}")

def main():
    print("Installing python-Levenshtein for better performance...")
    try:
        import subprocess
        subprocess.check_call(["pip", "install", "python-Levenshtein"])
    except:
        print("Could not install python-Levenshtein. Continuing with pure-python implementation.")

    try:
        matcher = UniversityMatcher('universities.csv', 'unis.csv')
        matcher.process_matches()
        matcher.update_universities()
        matcher.generate_report()
        matcher.save_results()
    except Exception as e:
        print(f"\nError occurred: {str(e)}")
        print("\nPlease verify:")
        print("1. Input files exist and are readable")
        print("2. Input files have the expected column structure")
        print("3. Data format is correct")

if __name__ == "__main__":
    main()