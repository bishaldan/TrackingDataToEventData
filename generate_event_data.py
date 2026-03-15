from FootballMatchAnalysis.analysis.events import *
from FootballMatchAnalysis.objects.match import Match
from FootballMatchAnalysis.analysis.xt import *
from FootballMatchAnalysis.analysis.xg import *
from FootballMatchAnalysis.analysis.utils import *
from FootballMatchAnalysis.analysis.zones import *
from parse_possessions import *
from collections import deque
import math
import pandas as pd

################### GETTING STARTED ###################
# This script was designed to convert tracking data to
# event data. Adjust the parameters below and run this 
# script to recieve event data folllowing Metrica's 
# standard. Once the script is complete, events will 
# be stored in the `df` dataframe.

# Data Source
DATADIR = './data'
game_id = 1

# Script Parameters
generate_video = False # Generate video from snalysis
print_frames = True    # Print Frames (for debuging)
start_frame = 0        # Start Frame
end_frame = 4000       # End Frame
#######################################################

def annotate_frame(plot, dq):
    i = 1
    plot.write("Raw Possesion Data:", -52, 32, justifification="left")

    for p in reversed(dq):
        poss_str = ""
        if p["Type"] == "Possesion":
            y = 32-(i*1.5)
            eframe = None
            if p["EndFrame"]:
                eframe = p["EndFrame"]
            player = f"P{p["Player"].name}"

            coords = ""
            if "StartXY" in p and len(p["StartXY"]) > 0:
                coords = f"({round(p["StartXY"][0], 1)},{round(p["StartXY"][1], 1)})"
            if "EndXY" in p and len(p["EndXY"]) > 0:
                coords += f", ({round(p["EndXY"][0], 1)},{round(p["EndXY"][1], 1)})"

            poss_str = f"{player} ({p["Team"][0]}) on ball, SFrame {p["StartFrame"]}, EFrame: {eframe}, Cords: {coords}"
            plot.write(poss_str, -52, y, justifification="left", font_size=8)
        else:
            poss_str = f"Ball out"
        i+=1

def annotate_events(plot, events_dq):
    plot.write("Events Found:", 1, 32, justifification="left")
    if len(events_dq) > 0:
        i = 1
        for p in reversed(events_dq):
            event_str = event_to_string(p)
            y = 32-(i*1.5)
            plot.write(event_str, 1, y, justifification="left", font_size=8)
            i+=1

def ball_maintains_direction(p1_start, p1_end, p2_start, p2_end,
                        angle_tol_deg=10,
                        collinear_tol=0.05):
    def vec(a, b):
        return (b[0] - a[0], b[1] - a[1])

    def norm(v):
        return math.hypot(v[0], v[1])

    def normalize(v):
        n = norm(v)
        if n == 0:
            return None
        return (v[0] / n, v[1] / n)

    v1 = vec(p1_start, p1_end)
    v2 = vec(p2_start, p2_end)

    n1 = normalize(v1)
    n2 = normalize(v2)

    if n1 is None or n2 is None:
        return False

    dot = n1[0] * n2[0] + n1[1] * n2[1]
    dot = max(-1.0, min(1.0, dot))

    angle = math.degrees(math.acos(dot))
    if angle > angle_tol_deg:
        return False

    cross = abs(
        (p2_start[0] - p1_start[0]) * v1[1] -
        (p2_start[1] - p1_start[1]) * v1[0]
    )

    line_len = norm(v1)
    if cross / line_len > collinear_tol:
        return False

    return True

def does_the_ball_come_back(i, player):
    frame_num = i
    while True:
        frame_num += 1
        frame = match.get_moment(frame_num)
        is_someone_on_ball = frame.possession(threshold=.75)
        if is_someone_on_ball:
            player_on_ball = frame.possession(threshold=1000)
            if(player_on_ball.name == player.name):
                return True
            else: 
                return False

def ball_goes_past_them(i, player):
    goes_past_them = False
    count = 0
    while (not goes_past_them and count < 5):
        count += 1
        i += 1
        frame = match.get_moment(i)
        is_someone_on_ball = frame.possession(threshold=.75)
        if is_someone_on_ball is None:
            goes_past_them = True
        else:
            if is_someone_on_ball.name != player.name:
                goes_past_them = True

    return goes_past_them

def find_last_player_on_ball(i, player):
    last_player = None
    while last_player is None:
        i -=1
        frame = match.get_moment(i)
        closest_player = frame.possession(threshold=.75)
        if closest_player:
            if player.name != closest_player.name:
                return i
        if i < 1:
            return 0

def find_next_player_on_ball(i, player):
    next_player = None
    while next_player is None:
        i +=1
        frame = match.get_moment(i)
        closest_player = frame.possession(threshold=.75)
        if closest_player:
            if player.name != closest_player.name:
                return i

def is_ball_out(ball):
    x = round(ball.x, 2)
    y = round(ball.y, 2)

    if x < -53 or x > 53:
        return True
    if y < -34 or y > 34:
        return True
    return False

def in_path_of_net(p1, p2):
    x1, y1 = p1
    x2, y2 = p2

    dx = x2 - x1
    dy = y2 - y1

    if dx == 0:
        return False

    NET_X = 53 if dx > 0 else -53
    NET_Y_MIN = -6
    NET_Y_MAX = 6

    t = (NET_X - x1) / dx

    if t <= 0:
        return False

    y_at_net = y1 + t * dy

    return NET_Y_MIN <= y_at_net <= NET_Y_MAX

def in_net(ball):
    x = round(ball.x, 2)
    y = round(ball.y, 2)
    
    if x <= -53 and x >= -56:
        if y <= 3.4 and y >= -3.4:
            return True
    elif x >= 53 and x <= 56:
        if y <= 3.4 and y >= -3.4:
            return True
    return False

def in_center(ball):
    x = round(ball.x, 2)
    y = round(ball.y, 2)
    
    if x < 0.5 and x > -0.5:
        if y < 0.5 and y > -0.5:
            return True
    return False

def out_of_endline(ball):
    x = round(ball.x, 2)
    y = round(ball.y, 2)
    
    if x < -53 or x > 53:
        if y > -34 or y < 34:
            return True
    return False

def out_of_touchline(ball):
    x = round(ball.x, 2)
    y = round(ball.y, 2)
    
    if x > -53 or x < 53:
        if y < -34 or y > 34:
            return True
    return False


# Load Match Data
plot = Plot()
match = Match(DATADIR, game_id)

# Set Up Dequeues
possession_dq = deque(maxlen=5)
events_dq = deque(maxlen=5)
possession_view_dq = deque(maxlen=3)

# Possession Data and Event Data
possessions = []
all_events = []

# Default Tracking State 
team_in_possession = None
ball_out = True
possession = { 
    "StartFrame" : None,
    "EndFrame" : None,
    "Team" : None,
    "Player" : None,
    "OnBall" : [],
    "Type" : None,
    "StartXY" : None
}

# Generate events
for i in range(start_frame, end_frame+1):
    # Get Frame Information
    frame = match.get_moment(i)
    if generate_video or print_frames:
        plot = frame.plot_moment()
    ball = frame.ball
    is_someone_on_ball = frame.possession(threshold=.75)
    closest_player = frame.possession(threshold=1000)
    num_on_ball = frame.players_competeing_for_ball()

    if closest_player:
        dist_from_ball = frame.distance_from_ball(closest_player)

        check = ""
        if is_someone_on_ball:
            team_in_possession = closest_player.team
            check = f"{team_in_possession} Team on Ball"

        print(f"Frame {i}: {round(dist_from_ball, 4)} {check} ")

        # Finding First Possession
        if len(possessions) == 0 and possession["StartFrame"] is None:
            if is_someone_on_ball:
                possession = { 
                    "StartFrame" : i,
                    "EndFrame" : None,
                    "Team" : closest_player.team,
                    "Player" : closest_player,
                    "OnBall" : num_on_ball,
                    "Type" : "Possesion",
                    "StartXY" : (ball.x, ball.y)
                }     
        else:
            if possession["StartFrame"] and possession["Type"] == "Ball Out":
                if ball is None:
                    # Ball Lost, do nothing
                    pass
                elif is_ball_out(ball):
                    # Ball still is out, do nothing
                    pass
                else:
                    # Ball is back
                    possession["EndFrame"] = i - 1
            elif is_ball_out(ball):
                # Ball is out of bounds
                possession = { 
                    "StartFrame" : i,
                    "EndFrame" : None,
                    "Team" : None,
                    "Player" : None,
                    "OnBall" : [],
                    "Type" : "Ball Out",
                    "StartXY" : (ball.x, ball.y)
                }    
            elif is_someone_on_ball:
                if len(possessions) > 0:
                    if possession["StartFrame"] and (closest_player.name == possession["Player"].name):
                        # Ball is still with current player
                        pass
                    elif closest_player.team != possessions[-1]["Team"]:
                        if ball_goes_past_them(i, closest_player):
                            last_point = find_last_player_on_ball(i, closest_player)
                            last_ball = match.get_moment(last_point).ball
                            next_point = find_next_player_on_ball(i, closest_player)
                            next_ball = match.get_moment(next_point).ball
                            if ball_maintains_direction((last_ball.x, last_ball.y),(ball.x, ball.y), (ball.x, ball.y), (next_ball.x, next_ball.y)):
                                # Ball moved past player and can be ignored
                                pass
                            else:
                                # Ball left Player, changed directions, likely intercepted
                                if possession["StartFrame"] is None:
                                    possession = { 
                                        "StartFrame" : i - 1,
                                        "EndFrame" : None,
                                        "Team" : closest_player.team,
                                        "Player" : closest_player,
                                        "OnBall" : num_on_ball,
                                        "Type" : "Possesion",
                                        "StartXY" : (ball.x, ball.y)
                                    }
                        else:
                            # Ball Sticks with Player, possession likely over
                            possession = { 
                                "StartFrame" : i - 1,
                                "EndFrame" : None,
                                "Team" : closest_player.team,
                                "Player" : closest_player,
                                "OnBall" : num_on_ball,
                                "Type" : "Possesion",
                                "StartXY" : (ball.x, ball.y)
                            }
                    elif possession["StartFrame"] is None:
                        possession = { 
                            "StartFrame" : i,
                            "EndFrame" : None,
                            "Team" : closest_player.team,
                            "Player" : closest_player,
                            "OnBall" : num_on_ball,
                            "Type" : "Possesion",
                            "StartXY" : (ball.x, ball.y)
                        }
            else:
                # Has a pass started?
                if possession["EndFrame"] is None:
                    if possession["Player"]:
                        if does_the_ball_come_back(i, possession["Player"]) == False:
                            possession["EndFrame"] = i - 1
                            possession["EndXY"] = (ball.x, ball.y)

        if possession["StartFrame"] is not None and possession["EndFrame"] is not None:
            # Add Completed Possession
            possessions.append(possession)
            possession_dq.append(possession)

            # Check for events to Eval
            possession_view_dq.append(possession)
            events, ball_out = review_events(possession_view_dq, ball_out)
            if events is not None:
                if "dict" in str(type(events)):
                    all_events.append(events)
                    events_dq.append(events)
                else:

                    for event in events:
                        all_events.append(event)
                        events_dq.append(event)
            if ball_out and len(possession_view_dq) > 2:
                p = possession_view_dq[2]
                possession_view_dq.clear()
                possession_view_dq.append(p)

            possession = { 
                "StartFrame" : None,
                "EndFrame" : None,
                "Team" : None,
                "Player" : None,
                "OnBall" : [],
                "Type" : None,
                "StartXY" : None
            }
        if generate_video:
            annotate_frame(plot, possession_dq)
            annotate_events(plot, events_dq)
            plot.print(f"./frames/{i}.png")
        elif print_frames:
            plot.print(f"./frames/{i}.png")

df = pd.DataFrame(events)