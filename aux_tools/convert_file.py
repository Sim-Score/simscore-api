import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pandas as pd
from typing import Tuple
from app.api.v1.models.request import IdeaRequest, IdeaInput, AdvancedFeatures

def convert_spreadsheet_to_request(
    file_path: str,
    id_column: str,
    data_column: str,
    advanced_features: AdvancedFeatures = {}
) -> IdeaRequest:
    """
    Convert a spreadsheet file to an IdeaRequest object.
    
    Args:
        file_path: Path to the spreadsheet file (xlsx, csv, etc)
        id_column: Name of the column containing IDs
        data_column: Name of the column containing idea text
        include_advanced_features: Whether to include advanced analysis features
        
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


if __name__ == "__main__":
    import argparse
    import pandas as pd
    import json
    
    parser = argparse.ArgumentParser(description='Convert spreadsheet to IdeaRequest format')
    parser.add_argument('file_path', help='Path to the spreadsheet file (xlsx or csv)')
    parser.add_argument('id_column', help='Name of the column containing IDs')
    parser.add_argument('data_column', help='Name of the column containing idea text')
    
    args = parser.parse_args()
    
    try:
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
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)
