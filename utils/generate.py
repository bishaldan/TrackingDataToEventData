import numpy as np

def generate_pass(last_possession, possession):
    return {
        "Team" : possession["Team"],
        "Type" : "PASS",
        "Subtype" : np.nan,
        "Period" : np.nan,
        "Start Frame" : last_possession["EndFrame"],
        "Start Time [s]" : round(last_possession["EndFrame"] / 24, 2),
        "End Frame" : possession["StartFrame"],
        "End Time [s]" : round(possession["StartFrame"] / 24, 2),
        "From" : f"Player{last_possession["Player"].name}",
        "To" : f"Player{possession["Player"].name}",
        "Start X" : round(last_possession["EndXY"][0], 2),
        "Start Y" : round(last_possession["EndXY"][1], 2),
        "End X" : round(possession["StartXY"][0], 2),
        "End Y" : round(possession["StartXY"][1], 2)
    }

def generate_interception(last_possession, possession):
    return [
        {
            "Team" : last_possession["Team"],
            "Type" : "BALL LOST",
            "Subtype" : "INTERCEPTION",
            "Period" : np.nan,
            "Start Frame" : last_possession["EndFrame"],
            "Start Time [s]" : round(last_possession["EndFrame"] / 24, 2),
            "End Frame" : possession["StartFrame"],
            "End Time [s]" : round(possession["StartFrame"] / 24, 2),
            "From" : f"Player{last_possession["Player"].name}",
            "To" : np.nan,
            "Start X" : round(last_possession["EndXY"][0], 2),
            "Start Y" : round(last_possession["EndXY"][1], 2),
            "End X" : round(possession["StartXY"][0], 2),
            "End Y" : round(possession["StartXY"][1], 2)
        },
        {
            "Team" : possession["Team"],
            "Type" : "RECOVERY",
            "Subtype" : "INTERCEPTION",
            "Period" : np.nan,
            "Start Frame" : possession["StartFrame"],
            "Start Time [s]" : round(possession["StartFrame"] / 24, 2),
            "End Frame" : possession["StartFrame"],
            "End Time [s]" : round(possession["StartFrame"] / 24, 2),
            "From" : f"Player{possession["Player"].name}",
            "To" : np.nan,
            "Start X" : round(possession["StartXY"][0], 2),
            "Start Y" : round(possession["StartXY"][1], 2),
            "End X" : np.nan,
            "End Y" : np.nan
        }
    ]

def generate_ball_out(last_possession, possession):
    return {
        "Team" : possession["Team"],
        "Type" : "BALL OUT",
        "Subtype" : np.nan,
        "Period" : np.nan,
        "Start Frame" : possession["EndFrame"],
        "Start Time [s]" : round(possession["EndFrame"] / 24, 2),
        "End Frame" : possession["StartFrame"],
        "End Time [s]" : round(possession["StartFrame"] / 24, 2),
        "From" : f"Player{last_possession["Player"].name}",
        "To" : np.nan,
        "Start X" : round(last_possession["EndXY"][0], 2),
        "Start Y" : round(last_possession["EndXY"][1], 2),
        "End X" : round(possession["StartXY"][0], 2),
        "End Y" : round(possession["StartXY"][1], 2)
    }

def generate_set_piece(possession, type):
    return {
        "Team" : possession["Team"],
        "Type" : "SET PIECE",
        "Subtype" : type,
        "Period" : np.nan,
        "Start Frame" : possession["StartFrame"],
        "Start Time [s]" : round(possession["StartFrame"] / 24, 2),
        "End Frame" : possession["StartFrame"],
        "End Time [s]" : round(possession["StartFrame"] / 24, 2),
        "From" : f"Player{possession["Player"].name}",
        "To" : np.nan,
        "Start X" : np.nan,
        "Start Y" : np.nan,
        "End X" : np.nan,
        "End Y" : np.nan
    }

def generate_goal(last_possession, possession):
    return {
        "Team" : last_possession["Team"],
        "Type" : "SHOT",
        "Subtype" : "ON TARGET-GOAL",
        "Period" : np.nan,
        "Start Frame" : last_possession["EndFrame"],
        "Start Time [s]" : round(last_possession["EndFrame"] / 24, 2),
        "End Frame" : possession["StartFrame"],
        "End Time [s]" : round(possession["StartFrame"] / 24, 2),
        "From" : f"Player{last_possession["Player"].name}",
        "To" : np.nan,
        "Start X" : round(last_possession["EndXY"][0], 2),
        "Start Y" : round(last_possession["EndXY"][1], 2),
        "End X" : round(possession["StartXY"][0], 2),
        "End Y" : round(possession["StartXY"][1], 2)
    }