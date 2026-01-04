import requests
import json
import os

# Configuration
API_URL = "http://localhost:3000/api/process-json"

def complete_floor_plan(wall_list, door_list, window_list, beam_list, column_list, room_list=None):
    """
    Completes a floor plan JSON by calculating outerPoints, totalArea, and centerPos via the Node.js API.
    
    Args:
        wall_list (list): List of wall objects.
        door_list (list): List of door objects.
        window_list (list): List of window objects.
        beam_list (list): List of beam objects.
        column_list (list): List of column objects.
        room_list (list, optional): List of existing room objects to maintain room names and identities.
        
    Returns:
        dict: The complete floor plan JSON with calculated fields (including roomList).
    """
    
    # Construct the partial JSON payload
    payload = {
        "version": "1.0",
        "unit": "mm",
        "wallList": wall_list,
        "roomList": room_list if room_list is not None else [],
        "doorList": door_list,
        "windowList": window_list,
        "beamList": beam_list,
        "columnList": column_list
    }
    
    try:
        print(f"Sending request to {API_URL}...")
        response = requests.post(API_URL, json=payload)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: API returned status code {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the API server. Is node server-api.js running?")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
