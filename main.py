import argparse
from doko_game.interface import interface_player
import json

default_args = {
    "played_cards": [],  # like hand string
    "playmode": 7,  # not further implemented
    "hochzeit_player": None,  # int from starter player else None
    "ansagen": [-1] * 4,  # True/False for re/kontra else -1 starting from starting player
    "elo": 2,  # int in [1, 3], higher = better, but slower
    "abfrage": False,
}


def translate(cards):
    """
    public function getAIString()
    {
        $farben = [1 => 'd', 2 => 'h', 3 => 's', 4 => 'c'];
        $werte = [1 => 'n', 2 => 'j', 3 => 'q', 4 => 'k', 5 => 't', 6 => 'a'];
    """
    farbe = {"c": 10, "s": 20, "h": 30, "d": 40}
    wert = {"n": 6, "j": 5, "q": 4, "k": 3, "t": 2, "a": 1}
    trumpf = [32, 14, 24, 34, 44, 15, 25, 35, 45, 41, 42, 43, 46]
    ret = []
    for i in cards:
        i = farbe[i[0]] + wert[i[1]]
        if i in trumpf:
            i += 100
        ret.append(i)
    return ret


def retranslate(card):
    farbe = {1: "c", 2: "s", 3: "h", 4: "d"}
    wert = {1: "a", 2: "t", 3: "k", 4: "q", 5: "j", 6: "n"}
    if card in [12, 13]:
        return str(card)
    return farbe[card % 100 // 10] + wert[card % 10]


def main(raw_args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("-json", required=True)
    args = parser.parse_args(raw_args)
    json_info = json.loads(args.json)
    # required
    inp = {"hand": translate(list(json_info["computer_player_hand"]))}
    # rest is optional
    try:
        inp["game"] = translate(list(json_info["played_cards"]))
    except KeyError:
        inp["game"] = []
    try:
        inp["hochzeit_player"] = int(json_info["hochzeit_player"])
    except KeyError:
        inp["hochzeit_player"] = None
    try:
        inp["ansagen"] = [int(i) for i in list(json_info["ansagen"])]
    except KeyError:
        inp["ansagen"] = default_args["ansagen"]
    try:
        inp["elo"] = int(json_info["elo"])
    except KeyError:
        inp["elo"] = default_args["elo"]
    try:
        inp["playmode"] = int(json_info["playmode"])
    except KeyError:
        inp["playmode"] = default_args["playmode"]
    try:
        inp["abfrage"] = bool(json_info["abfrage"])
    except KeyError:
        inp["abfrage"] = default_args["abfrage"]

    max_card = interface_player(inp["hand"], inp["game"],
                                inp["playmode"], inp["ansagen"],
                                inp["hochzeit_player"], inp["elo"],
                                inp["abfrage"])

    max_card = json.dumps({'best_card': retranslate(max_card)})
    print(max_card)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({"error": e}))
