def is_ball_in_corner(x,y):
    if x < 52 and x > -52:
        return False
    else:
        if y < 33 and y > -33:
            return False

    return True

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

def in_net(x, y):
    x = round(x, 2)
    y = round(y, 2)
    
    if x <= -53 and x >= -56:
        if y <= 3.4 and y >= -3.4:
            return True
    elif x >= 53 and x <= 56:
        if y <= 3.4 and y >= -3.4:
            return True
    return False

def is_ball_in_center(x,y):
    return True

def is_ball_past_goal_line(x,y):
    return True

def is_ball_past_end_line(x,y):
    return True

def event_to_string(event):
    if event['Type'] == "PASS":
       return f"{event["To"]} {event['Type']} to {event["From"]}"
    elif event['Type'] in ["BALL LOST", "RECOVERY", "SHOT"]:
        return f"{event["From"]} {event['Type']} ({event['Subtype']})"
    elif event['Type'] == "SET PIECE":
       return f"{event['Subtype']}"
    else:
        return f"{event['Type']}"