import re
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pandas as pd
import json
from typing import Tuple
from app.api.v1.models.request import IdeaRequest, IdeaInput, AdvancedFeatures

def convert_harmonica_to_request(
    file_path: str,
    advanced_features: AdvancedFeatures = {}
) -> IdeaRequest:
    """Convert Harmonica chat data to IdeaRequest with paragraphs as separate ideas"""
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    ideas = []
    idea_id = 1
    
    for entry in data:
        chat_text = entry['chat_text']
        user_name = entry['user_name']
       
        # Split by both user and assistant markers
        parts = re.split(r'user : |assistant : ', chat_text)      
        # First part is empty since chat starts with a marker
        parts = [p for p in parts if p.strip()]
        
        # Alternate between user and assistant for each part
        for i, text in enumerate(parts):
            speaker = "user" if i % 2 == 0 else "assistant"
            paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
                    
            for para in paragraphs:
                ideas.append(IdeaInput(
                    id=str(idea_id),
                    idea=para,
                    author_id=f"{user_name}_{speaker}"
                ))
                idea_id += 1        
    
    return IdeaRequest(
        ideas=ideas,
        advanced_features=advanced_features
    )

def convert_spreadsheet_to_request(
    file_path: str,
    id_column: str,
    data_column: str,
    advanced_features: AdvancedFeatures = {}
) -> IdeaRequest:
    """
    Convert a spreadsheet file to an IdeaRequest object.
    
    Use this with pythonpath adjusted like so:
    PYTHONPATH=$PYTHONPATH:/home/path/to/simscore-api python aux_tools/convert_file.py 'file.csv' id_col_header data_col_header 
    
    Args:
        file_path: Path to the spreadsheet file (xlsx, csv, etc)
        id_column: Name of the column containing IDs
        data_column: Name of the column containing idea text
        advanced_features: Whether to include advanced analysis features
        
    Returns:
        IdeaRequest object ready for the /rank-ideas endpoint
    """
    # Read spreadsheet based on file extension
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)
    
    # Validate columns exist
    if id_column not in df.columns or data_column not in df.columns:
        raise ValueError(f"Columns {id_column} and/or {data_column} not found in spreadsheet")
    
    # Convert rows to IdeaInput objects
    ideas = [
        IdeaInput(
            id=str(row[id_column]),  # Convert to string to handle various ID formats
            idea=str(row[data_column]).strip(),
        )
        for _, row in df.iterrows()
        if pd.notna(row[data_column])  # Skip rows with empty ideas
    ]
    
    # Create request object
    request = IdeaRequest(
        ideas=ideas,
        advanced_features=advanced_features
    )
    
    return request

def convert_request_to_spreadsheet(request_data: dict, output_path: str = "output.xlsx") -> None:
    """Convert IdeaRequest JSON to spreadsheet with Id, Author, Role, Idea columns"""
    # Extract ideas from request
    ideas = request_data["ideas"]
    
    # Create lists for each column
    data = {
        "Id": [],
        "Author": [],
        "Idea": []
    }
    
    # Define lines to exclude
    exclude_lines = [
        "User shared the following context:",
        "preferred_language: "
    ]
    
    # Parse each idea entry
    for idea in ideas:        
      if any(idea["idea"].startswith(line) for line in exclude_lines):
        continue
      
      if idea["author_id"].endswith('_user'):
        data["Id"].append(idea["id"])
        data["Author"].append(idea["author_id"])
        data["Idea"].append(idea["idea"])
    
    # Create DataFrame and save to Excel
    df = pd.DataFrame(data)
    df.to_excel(output_path, index=False)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert file to IdeaRequest format')
    parser.add_argument('file_path', help='Path to the input file (xlsx, csv, or json)')
    parser.add_argument('--id_column', help='Name of the column containing IDs (for spreadsheets)')
    parser.add_argument('--data_column', help='Name of the column containing idea text (for spreadsheets)')
    parser.add_argument('--save_as_spreadsheet', help='Save the output as spreadsheet (for json input)')
    
    args = parser.parse_args()
    
    try:
        if args.file_path.endswith('.json'):
            request = convert_harmonica_to_request(args.file_path, 
                          AdvancedFeatures(relationship_graph=True, 
                                           pairwise_similarity_matrix=True, 
                                           cluster_names=True)
                      )
            print(f"Successfully converted {len(request.ideas)} paragraphs from chat data.")
        else:
            if not args.id_column or not args.data_column:
                raise ValueError("id_column and data_column are required for spreadsheet conversion")
            request = convert_spreadsheet_to_request(
                file_path=args.file_path,
                id_column=args.id_column,
                data_column=args.data_column
            )
            print(f"Successfully converted {len(request.ideas)} ideas from spreadsheet.")
        
        # Write request to file
        output_file = "request.json"
        with open(output_file, "w") as f:
            json.dump(request.dict(), f, indent=2)
        print(f"Request written to {output_file}")
        
        if args.save_as_spreadsheet:
            convert_request_to_spreadsheet(request.dict(), "output.xlsx")

    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)
