import time
from typing import List
from doko_game.ismcts import ismcts, Doko_ISMCTS
import numpy as np


def interface_player(cards: List[int], game: List[int],
                     playmode: int, ansagen: List[int], hochzeit_player=None, strength=2):
    """
    cards = [12, 13, ...] list of ints of cards on hand
    game = [12, 13, ...] list of int !! with trumpf > 100
    ansagen: [True, False, -1, -1] list of bool and -1
    playmode: nothing else than 7 right now
    hochzeit_player: int if not None
    strength: int: [1-3] for tree search length
    get info, make rootstate with book, don't reset, start search, prints results
    """
    assert playmode == 7, "nothing else implemented"
    assert 1 <= len(cards) <= 12, "card length wrong"
    assert 0 <= len(game) <= 48, "game length wrong"
    assert len(ansagen) == 4
    assert 1 <= strength <= 3
    start = time.time()
    rs = Doko_ISMCTS()
    rs.realdoko.playmode = playmode
    doko = rs.realdoko
    if hochzeit_player is not None:
        doko.book.solo = True
        doko.book.hochzeit = True
        for player in range(4):
            if player == hochzeit_player:
                doko.book.re_on_hand[player] = True
                doko.book.re[player] = True
            else:
                doko.book.re_on_hand[player] = False
                doko.book.re[player] = False

    doko.player_to_play = 0
    game = game + [0] * (48 - len(game))
    doko.game = game
    doko.book.ansage = ansagen
    doko.book.re = ansagen if not doko.book.hochzeit else doko.book.re
    doko.previous_player = -1
    doko.card_number = 0

    for i in range(0, 48, 4):
        stich = game[i:i+4]
        if 0 in stich:
            break
        doko.previous_player = doko.player_to_play
        doko.bedien = stich[0]
        for card in stich:
            doko.book.update(doko.bedien, card, doko.player_to_play, doko)
        winner = 0
        for order in range(1, 4):
            if doko._check_higher(stich[winner], stich[order]):
                winner = order
        doko.player_to_play = (doko.player_to_play + 1 + winner) % 4
        # append to haufen, player_to_player is now winner
        stichwert = sum([doko.wert_by_last[int(i % 10)] for i in stich])
        # doppelkopf, charlie, fuchs
        if stichwert >= 40:
            doko.doppelkopf[doko.player_to_play] += 1
        doko.haufen[doko.player_to_play] += stichwert
        for idx, card in enumerate(stich):
            if card == 41:
                # winner and fuchs player
                doko.fuchs.append(doko.player_to_play)
                doko.fuchs.append((doko.previous_player + 1 + idx) % 4)
        # if hochzeit and stich is below 4, and winner is not hochzeitplayer and still solo
        # not solo anymore, change teams, update book
        if doko.book.hochzeit and doko.book.solo and \
                doko.card_number < 12 and not doko.book.re[doko.player_to_play]:
            doko.book.solo = False
            doko.book.re[doko.player_to_play] = True
            doko.book.re_on_hand[doko.player_to_play] = False
        doko.card_number += 4

    doko.bedien = game[doko.card_number - doko.card_number % 4]
    doko.bedien = doko.bedien if doko.bedien != 0 else -1
    for card in game[doko.card_number:]:
        if card != 0:
            doko.card_number += 1
            doko.book.update(doko.bedien, card, doko.player_to_play, doko)
            doko.player_to_play = int((doko.player_to_play + 1) % 4)
        else:
            break
    rs.playerToMove = doko.player_to_play
    doko.hands[doko.player_to_play] = cards + [0] * (12 - len(cards))
    doko.abfrage = False
    itermax = {1: 1000, 2: 7000, 3: 50000}[strength]  # game len?, 800 it/s
    move, rootnode = ismcts(rs, int(itermax))
    options_sorted = sorted(rootnode.childNodes, key=lambda c: c.visits, reverse=True)
    move_options = [i.move for i in options_sorted]
    value_options = [i.wins for i in options_sorted]
    visit_options = [i.visits for i in options_sorted]
    time.sleep(max(0., 1 - time.time() - start))
    if doko.abfrage:
        # print(f"mcts prefers {'keine ansage' if move_options[0] == 13 else 'ansage'}")
        return move_options[0]
    else:
        move_options = [rs.realdoko.hands[rs.playerToMove][i] for i in move_options]
        return move_options[0]


if __name__ == "__main__":
    sample_doko = Doko_ISMCTS().realdoko
    x = sample_doko.all_cards
    # (itermax: int, cards: List[int], game: List[int], start_player: int,
    #                      playmode: int, ansagen: List[int], hochzeit_player=None)
    test_cases = [
        [np.random.choice(x, size=12, replace=False).tolist(), [], 7, [-1] * 4, ],
        [np.random.choice(x, size=12, replace=False).tolist(), [11, 16, 12], 7, [-1] * 4],
        # [[132, 132, 124, 124, 134, 134, 144, 144, 115, 115, 11, 12], [], 7, [False, -1, -1, -1], 2],
    ]
    for case in test_cases:
        print("=" * 80)
        print("game", sample_doko.translate(case[1]))
        print("hand", sample_doko.translate(sample_doko.order_hand(case[0])))
        interface_player(*case, strength=1)
        interface_player(*case, strength=2)
        # interface_player(*case, strength=3)
        # interface_player(100000, *case)
