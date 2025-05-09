#!/usr/bin/env python3

import os
import re
import json
import csv
from bs4 import BeautifulSoup
import locale
from datetime import datetime
from pathlib import Path

from typing import Dict, List, Union, TypedDict, Optional


locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')

def extract_contributions(html_file):
    """
    Extract contribution data from an HTML file.

    Args:
        html_file (str): Path to the HTML file

    Returns:
        list: List of dictionaries containing contribution data
    """
    with open(html_file, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file.read(), 'html.parser')

    contributions = []

    # Find all contribution divs with class "one-obs"
    for contrib_div in soup.find_all('div', class_='one-obs'):
        # Initialize contribution with default values
        contribution: Dict[str, Union[None, int, str, datetime]] = {
            'number': None,
            'user': None,
            'time': None,
            'body': None
        }

        # Extract contribution number from h2 tag
        h2_tag = contrib_div.find('h2')
        number_match = re.search(r'(\d+)\s', h2_tag.text.strip())
        if h2_tag and number_match:
            contribution['number'] = number_match.group(1)

        # Extract user info and post time from div with class "infos-obs"
        info_div = contrib_div.find('div', class_='infos-obs')
        if info_div:
            # Extract user name
            user_info = info_div.get_text().strip()

            # Extract username using regex to handle different formats
            user_match = re.search(r'Anonyme|Par\s+(.+?)\n', user_info)
            if user_match:
                if 'Anonyme' in user_match.group(0):
                    contribution['user'] = 'Anonyme'
                else:
                    contribution['user'] = user_match.group(1).strip() if user_match.group(1) else 'Unknown'

            # Extract post time
            time_match = re.search(r'Déposée\s+le\s+(.+)', user_info)
            if time_match:
                contribution['time'] = datetime.strptime(time_match.group(1).strip(), "%d %B %Y à %Hh%M")


        # Try to extract contribution body from span with class "obs-hide"
        body_div = contrib_div.find('span', class_='obs-hide')
        if body_div:
            contribution['body'] = body_div.get_text().strip()
        else:
            # If not found in span, try to find in div with class "obs-hide"
            body_div_alt = contrib_div.find('div', class_='obs-hide')
            if body_div_alt and body_div_alt.get_text().strip():
                contribution['body'] = body_div_alt.get_text().strip()
            else:
                # If still not found, try to get content from obs-content div
                content_div = contrib_div.find('div', class_='obs-content')
                if content_div:
                    contribution['body'] = content_div.get_text().strip()

        contributions.append(contribution)

    return contributions

def save_to_json(contributions, output_file):
    """
    Save contributions to a JSON file.

    Args:
        contributions (list): List of contribution dictionaries
        output_file (str): Path to the output JSON file
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(contributions, f, ensure_ascii=False, indent=4, sort_keys=True, default=str)
        f.write('\n' if contributions else '')
    print(f"Saved {len(contributions)} contributions to {output_file}")

def save_to_csv(contributions, output_file):
    """
    Save contributions to a CSV file.

    Args:
        contributions (list): List of contribution dictionaries
        output_file (str): Path to the output CSV file
    """
    if not contributions:
        print("No contributions to save.")
        return

    # Get the fieldnames from the first contribution
    fieldnames = contributions[0].keys()

    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(contributions)
    print(f"Saved {len(contributions)} contributions to {output_file}")

def main():
    working_dir: Path = Path(__file__).resolve().parent
    # Directory containing HTML files
    data_dir = working_dir / 'scrap-data' / 'scrap-data-250430T165525'

    # Get all HTML files in the directory
    html_files = list(data_dir.glob('*.html'))

    all_contributions = []

    # Process each HTML file
    for html_file in html_files:
        print(f"Processing {html_file}...")
        contributions = extract_contributions(html_file)
        all_contributions.extend(contributions)
        print(f"Found {len(contributions)} contributions in {html_file}")

    print(f"Total contributions extracted: {len(all_contributions)}")

    # Save the extracted data to files
    output_dir = data_dir / "extracted"
    output_dir.mkdir(exist_ok=True)

    save_to_json(all_contributions, str(output_dir / 'contributions.json'))
    save_to_csv(all_contributions, str(output_dir / 'contributions.csv'))

    # Print a sample of the extracted data
    if all_contributions:
        print("\nSample contribution:")
        sample = all_contributions[0]
        print(f"Number: {sample['number']}")
        print(f"User: {sample['user']}")
        print(f"Time: {sample['time']}")
        print(f"Body: {sample['body'][:100]}...")

if __name__ == "__main__":
    main()
