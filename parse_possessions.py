from utils.generate import *
from utils.utils import *

def review_events(events_dq, ball_out):
    if len(events_dq) < 3:
        return (None, ball_out)

    p1 = events_dq[0]
    p2 = events_dq[1]
    p3 = events_dq[2]

    if(p2["Type"] == "Ball Out"):
        is_in_path = in_path_of_net(p1["EndXY"], p2["StartXY"])
        is_in_net = in_net(p2["StartXY"][0], p2["StartXY"][1])
        if is_in_net and is_in_path:
            #Goal
            return (generate_goal(p1, p2), True)
        else:
            return (generate_ball_out(p1, p2), True)
    else:
        set_piece = None
        if ball_out == True:
            #TODO: Decide set piece type from ball location
            if(is_ball_in_corner(p1["StartXY"][0], p1["StartXY"][1])):
                #Corner
                set_piece = generate_set_piece(p1, "CORNER KICK")
            elif(is_ball_in_center(p1["StartXY"][0], p1["StartXY"][1])):
                #Kick Off
                set_piece = generate_set_piece(p1, "KICK OFF")

            ball_out = False

        #Evaluate Events
        evens = None
        if p1["Team"] == p2["Team"]:
            #Completed Pass
            events = [ generate_pass(p1, p2) ]
        else: 
            #Interception
            is_interception = 1

            #Checking there wasn't a miss-labeling from players being too close
            if len(p2["OnBall"]) > 1:
                if p1["Team"] == p3["Team"]:
                    #TODO: Add check to ensure ball has traveled
                    #TODO: Consider time gating this check
                    has_right_team = 0
                    for p in p2["OnBall"]:
                        if p.team == p1["Team"]:
                            has_right_team = 1
                            p2["Team"] = p.team
                            p2["Player"] = p
                    if has_right_team:
                        is_interception = 0
            
            if is_interception:
                events = generate_interception(p1, p2)
            else:
                events = [ generate_pass(p1, p2) ]

        if events:
            if set_piece:
                return ( [ set_piece ] + events , False )
            else:
                return ( events, False )
            