import os
import csv
import json


def process_csv(file_path):
    courses = []
    with open(file_path, "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            courses.append(
                {
                    "Course Name": row["Course Name"],
                    "Institution Name": row["Institution Name"],
                    "Abbrv.": row["Abbrv."],
                    "Direct Entry Requirements": row["Direct Entry Requirements"],
                    "UTME Requirements": row["UTME Requirements"],
                    "Subjects": row["Subjects"],
                }
            )
    return courses


def extract_state(institution_name):
    if "ABUJA" in institution_name:
        return "FCT, ABUJA"
    else:
        parts = institution_name.split(",")
        last_part = parts[-1].strip()
        if "STATE" in last_part:
            return last_part.replace(" STATE", "")
    return "UNKNOWN"


def process_directory(directory):
    result = {}
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isdir(item_path):
            result[item] = process_directory(item_path)
        elif item.endswith(".csv"):
            university_name = (
                item.replace(".csv", "")
                .replace("___", " ")
                .replace("__", " ")
                .replace("_", " ")
            )
            courses = process_csv(item_path)
            state = (
                extract_state(courses[0]["Institution Name"]) if courses else "UNKNOWN"
            )
            if state not in result:
                result[state] = {}
            result[state][university_name] = courses
    return result


def main():
    base_dir = "x/institutions"
    output = process_directory(base_dir)

    with open("universities.json", "w") as jsonfile:
        json.dump(output, jsonfile, indent=2)


if __name__ == "__main__":
    main()
