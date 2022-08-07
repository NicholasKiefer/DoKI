import datetime
import pathlib
import pdb
import random

# import numpy as np

"""
to make this competible, we need:
hochzeit
re kontra ansagen,
interface,
füchse, superschwein?, charlie
mehr ansagen,
soli
armut, schmeißen

misalignment: stille hochzeit not possible, because fuck you
"""


class Doko:
    def __init__(self, seed, *args):
        self.seed = seed
        self.action_space = list(range(12))
        self.ansage_action = 13

        # todo: simplify
        if args:
            (self.player_to_play, self.previous_player, self.card_number,
             self.bedien, self.game, self.haufen, self.abfrage, self.doppelkopf,
             self.karlchen, self.fuchs) = args
        else:
            self.player_to_play = -1
            self.previous_player = -1
            self.card_number = -1
            self.bedien = -1
            self.game = [0] * 48
            self.haufen = [0] * 4
            self.abfrage = True
            self.doppelkopf = [0] * 4
            self.karlchen = [0] * 4
            self.fuchs = [0] * 4
        self.book = Book()
        self.hands = [[], [], [], []]
        self.done = False

        self.playmode = 7
        self.TRUMPF = [32, 14, 24, 34, 44, 15, 25, 35, 45, 41, 42, 43, 46]
        self.wert_by_last = {1: 11, 2: 10, 3: 4, 4: 3, 5: 2, 6: 0}
        self.all_cards = [32, 14, 24, 34, 44, 15, 25, 35, 45, 41, 42, 43, 46,
                          11, 12, 13, 16, 21, 22, 23, 26, 31, 33, 36] * 2
        self.all_cards = [i + 100 if i in self.TRUMPF else i for i in self.all_cards]
        self.TRUMPF = [i + 100 for i in self.TRUMPF]
        self.farbe = {1: "kreuz", 2: "pik", 3: "herz", 4: "karo"}
        self.bild = {1: "as", 2: "zehn", 3: "könig", 4: "dame", 5: "bube", 6: "neun"}
        self.backfarbe = {"kreuz": 10, "pik": 20, "herz": 30, "karo": 40}
        self.backbild = {"as": 1, "zehn": 2, "könig": 3, "dame": 4, "bube": 5, "neun": 6}
        self.kreuzdame = 114
        self.kreuzbube = 15

    def step(self, action):
        if self.abfrage:
            self.abfrage = False
            reward = 0
            if action == 12:
                # find out by book or hand what ansage the player is making
                if self.book.re[self.player_to_play] != -1:
                    self.book.update(-1, self.book.re[self.player_to_play], self.player_to_play, self)
                else:
                    self.book.update(-1, self.kreuzdame in self.hands[self.player_to_play], self.player_to_play, self)
            else:
                pass  # no ansage, nothing happens

        else:
            self.previous_player = self.player_to_play
            # do action, change game and hand
            # todo: action should be card directly, set first finding to zero in hand
            played_card = self.hands[self.player_to_play][action]
            assert played_card != 0
            self.game[self.card_number] = played_card
            self.hands[self.player_to_play][action] = 0
            self.book.update(self.bedien if self.card_number % 4 != 0 else -1, played_card, self.player_to_play, self)

            # if stich is finished determine winner
            if self.card_number % 4 == 3:
                self.bedien = -1
                stich = self.game[self.card_number - 3: self.card_number + 1]
                winner = 0
                for order in range(1, 4):
                    if self._check_higher(stich[winner], stich[order]):
                        winner = order
                self.player_to_play = (self.player_to_play + 1 + winner) % 4
                # append to haufen, player_to_player is now winner
                stichwert = sum([self.wert_by_last[int(i % 10)] for i in stich])
                # doppelkopf, charlie, fuchs
                if stichwert >= 40:
                    self.doppelkopf[self.player_to_play] += 1
                self.haufen[self.player_to_play] += stichwert
                if self.card_number == 47:
                    if not all([i != -1 for i in self.book.re]):
                        pdb.set_trace()
                    # assert all([i != -1 for i in self.book.re])
                    self.done = True
                    for idx, card in enumerate(stich):
                        if card == self.kreuzbube:
                            if idx == winner or \
                                    self.book.re[self.player_to_play] != self.book.re[(self.previous_player + 1 + idx) % 4]:  # player_to_play team different to card team
                                self.karlchen[self.player_to_play] += 1
                for idx, card in enumerate(stich):
                    if card == 41:
                        self.fuchs.append(self.player_to_play)
                        self.fuchs.append((self.previous_player + 1 + idx) % 4)
                # if hochzeit and stich is below 4, and winner is not hochzeitplayer and still solo
                # not solo anymore, change teams, update book
                if self.book.hochzeit and self.book.solo and \
                        self.card_number < 12 and not self.book.re[self.player_to_play]:
                    # pdb.set_trace()
                    self.book.solo = False
                    self.book.re[self.player_to_play] = True
                    self.book.re_on_hand[self.player_to_play] = False

            else:
                if self.card_number % 4 == 0:
                    self.bedien = played_card
                self.player_to_play = int((self.player_to_play + 1) % 4)

            self.card_number += 1
            if self.card_number < 8:
                self.abfrage = True if self.book.ansage[self.player_to_play] == -1 else False
                if self.abfrage:
                    # fuck, if team partner made ansage already, no longer possible...
                    possible_ansage = self.book.re[self.player_to_play] if (self.book.re[self.player_to_play] != -1) else (self.kreuzdame in self.hands[self.player_to_play])
                    self.abfrage = True if (possible_ansage not in self.book.ansage) else False
            else:
                self.abfrage = False
            if self.done:
                reward = self.calculate_reward()
                # only take reward for last player for muzero atleast
                reward = reward[self.previous_player]
                # observation = self.game + [0] * 12
            else:
                reward = 0
        # return self.observe(), reward, self.done
        return None, reward, self.done

    def to_play(self):
        return self.player_to_play

    def legal_actions(self):
        if self.abfrage:
            ret = [12, 13]
        else:
            hand = self.hands[self.player_to_play]
            if self.kreuzdame in hand and self.book.re_on_hand[self.player_to_play] == False:
                raise ValueError("re on hand but re_on_hand False")
                # breakpoint()
            if self.card_number % 4 == 0:
                ret = [idx for idx, i in enumerate(hand) if i != 0]
            else:
                # we get a color, if that color is on hand, only cards of that color are allowed
                # else every nonzero card is allowed
                if self.bedien // 100 == 1:
                    allowed_cards = [idx for idx, i in enumerate(hand) if i // 100 == 1]
                else:
                    color = self.bedien // 10
                    allowed_cards = [idx for idx, i in enumerate(hand) if i // 10 == color and i // 100 == 0]
                if len(allowed_cards) == 0:
                    ret = [idx for idx, i in enumerate(hand) if i != 0]
                else:
                    ret = allowed_cards
            if not all([self.hands[self.player_to_play][i] != 0 for i in ret]):
                pdb.set_trace()
        return ret

    def reset(self):
        # empty game list, full hand list and shuffle, and give back initial observation
        # also set player_to_play
        # inital observation is hand plus empty game
        self.game = [0] * 48
        self.hands = self.all_cards
        self.done = False
        self.bedien = -1
        self.haufen = [0] * 4
        self.book = Book()

        np.random.shuffle(self.hands)
        for i in range(0, 48, 12):
            hand = self.hands[i:i + 12]
            if sum([i == self.kreuzdame for i in hand]) > 1:
                self.book.hochzeit = True
                self.book.solo = True

        self.hands = [self.hands[i:i + 12] for i in range(0, 48, 12)]
        self.player_to_play = int(random.randint(0, 3))
        # observation = self.game + self.hands[self.player_to_play]
        self.card_number = 0

        # teams
        if self.book.hochzeit:
            for player in range(4):
                hand = self.hands[player]
                if self.kreuzdame in hand:
                    self.book.re_on_hand[player] = True
                    self.book.re[player] = True
                else:
                    self.book.re_on_hand[player] = False
                    self.book.re[player] = False
        # return self.observe()

    def observe(self):
        observation = self.game + self.book.ansage + self.book.re_on_hand
        observation = np.array([observation], dtype="int32").view((1, 1, -1))
        return observation

    def render(self):
        game_trans = self.translate(self.game)
        print(
            f"game: "
            f"{[game_trans[i:i + 4] for i in range(0, 48, 4) if not all([j == 0 for j in game_trans[i:i + 4]])][-2:]}")
        team = {True: "re", False: "kontra", -1: "don't know"}
        print(f"player: {self.player_to_play}({team[self.book.re[self.player_to_play]]})"
              f"with hand: "
              f"{self.translate(self.order_hand(self.hands[self.player_to_play]))}")
        # print("all hands: ", [self.translate(self.order_hand(i)) for i in self.hands])
        print("haufen: ", self.haufen)
        print("re:", self.book.re)
        print("ansage", self.book.ansage)

    def _check_higher(self, card1, card2):
        """
        always use:
        // 100 = 1 is trumpf
        // 10 = color
        % 10 = nearly wert
        checks if card2 is higher than card1
        core of game, should be fast. ranking of cards depends on playmode, load beforehand
        ranking should be fixed, besides that we have to deal with not-trumpf
        basic idea:
            if first not trumpf, second trumpf -> return True
            if first not trumpf, second not trumpf -> check if different color -> check not trumpf ranking
            if first trumpf, second trumpf -> check ranking
            if first trumpf, second not trumpf -> return False
        where trumpf depends on playmode
        """
        if card1 // 100 == 0:
            if card2 // 100 == 1:
                return True
            if card2 // 10 != card1 // 10:
                return False
            # cards have same not trumpf color -> ranking (lower second index wins)
            if card1 % 10 <= card2 % 10:
                return False
            return True
        else:
            if card2 // 100 == 0:
                return False
            # cards are both trumpf -> ranking (playmode dependant)
            if card1 == 32 and card2 == 32 and self.playmode in range(1, 8):
                if self.card_number // 4 >= 11:
                    return True
                else:
                    return False
            if self.TRUMPF.index(card1) <= self.TRUMPF.index(card2):
                return False
            return True

    def calculate_reward(self):
        # todo: more than ansagen
        resum = [i for index, i in enumerate(self.haufen) if self.book.re[index] == True]
        resum = sum(resum)
        kontrasum = [i for index, i in enumerate(self.haufen) if self.book.re[index] == False]
        kontrasum = sum(kontrasum)
        # assert resum == 240 - kontrasum
        if not resum == 240 - kontrasum:
            pdb.set_trace()
        re_won = True if resum > 120 else False
        total_points = max(0, (resum if re_won else kontrasum) // 30 - 3)
        total_points += 1 if (not re_won and self.playmode == 7) else 0
        total_points += 2 * sum([i != -1 for i in self.book.ansage])
        vor = [(1 if re_won else -1) * (1 if i else -1) for i in self.book.re]
        if self.book.solo:
            table = [total_points * i for i in vor]
            table = [i * 3 if self.book.re[idx] else i for idx, i in enumerate(table)]
        else:
            # karlchen, fuchs, doppelkopf everything from re point of view
            doppelkopf = sum([i * (1 if self.book.re[idx] == True else -1) for idx, i in enumerate(self.doppelkopf)])
            karlchen = sum([i * (1 if self.book.re[idx] == True else -1) for idx, i in enumerate(self.karlchen)])
            fuchs = 0
            for pair in range(0, len(self.fuchs), 2):
                if self.book.re[self.fuchs[pair]] != self.book.re[self.fuchs[pair + 1]]:
                    fuchs += 1 if self.book.re[self.fuchs[pair]] else -1
            table = [(total_points + doppelkopf + karlchen + fuchs) * i for i in vor]
        if not sum(table) == 0:
            pdb.set_trace()
        # assert sum(table) == 0
        return table

    def expert_action(self):
        raise NotImplementedError

    def untranslate(self, hand):
        translation = []
        for i in hand:
            i = str(i).split()
            card = self.backfarbe[i[0]] + self.backbild[i[1]]
            translation.append(int(card))
        return translation

    def translate(self, hand):
        translation = []
        for i in hand:
            if i != 0:
                card = f"{self.farbe[i % 100 // 10]} {self.bild[i % 10]}"
                translation.append(card)
        return translation

    def order_hand(self, hand):
        trumpf = []
        not_tr = []
        for i in hand:
            if i != 0:
                if i in self.TRUMPF:
                    trumpf.append(i)
                else:
                    not_tr.append(i)
        ordered = sorted(trumpf, key=lambda x: self.TRUMPF.index(x))
        not_tr = sorted(not_tr)
        return ordered + not_tr


class Book:
    def __init__(self, *args):
        """
        we follow conventions:
        if -1: not yet known
        if True: color is on hand
        if False: color is not on hand

        only important is re_on_hand: influenced by ansage, hochzeit and other players being re

        this book is basically an outside observer only seeing the game not the hands
        at giveout we add observer info to it and forget it afterwards again
        """
        if args:
            (self.trumpf, self.ansage, self.re_on_hand, self.re, self.hochzeit, self.solo,
             self.colors) = args
        else:
            self.trumpf = [-1] * 4
            self.ansage = [-1] * 4  # find out by action
            self.even_more = [-1] * 4
            self.re_on_hand = [-1] * 4  # find out by ansage or hochzeit
            self.re = [-1] * 4  # extra tracker
            self.hochzeit = False
            self.solo = False
            self.colors = [-1] * 16
        self.kreuzdame = 114

    def update(self, bedien, played_card, player: int, state=None):
        """
        end goal is CAN re_on_hand
        hochzeit: immediatly determines that, keep flag for second kreuzdame, because: still has both and says
                    something: after first re card still has on hand, but partner is re and does NOT have re
                    basically: re on hand for hochzeit player always, for team member never
        ansage: can re_on_hand yes, after laying down, not anymore, but there's only one left
                can re_on_hand no, determines nearly nothing
        case:
        [re, kontra, legt re, ?] -> kd give -> 4th player has to say no
        -> is_re = [True, False, True, ?]
        """
        # if not same color, cross of color
        # trumpf
        if played_card == -1:
            pass
        elif played_card in [True, False]:
            # ansage
            self.ansage[player] = played_card
            self.re[player] = played_card
            if not sum([i != -1 for i in self.ansage]) < 3:
                breakpoint()
            # assert sum([i != -1 for i in self.ansage]) < 3
        else:
            if bedien != -1:
                if bedien // 100 == 1:
                    if played_card // 100 == 0:
                        self.trumpf[player] = False
                # color
                else:
                    if played_card // 10 != bedien // 10:
                        self.colors[player * 4 + bedien // 10 - 1] = False
            if not self.hochzeit and not self.solo:
                if played_card == self.kreuzdame:
                    self.re[player] = True
                    self.re_on_hand[player] = False

        self.infer_team_update()

    def infer_team_update(self):
        # inference step, determine teams if possible, by re
        # if already determined: skip step
        if (-1 not in self.re) or self.solo or self.hochzeit:
            pass
        else:
            # special case where re or kontra said, but nothing yet played: re on hand dependent on ansage
            for player in range(4):
                if self.ansage[player] != -1 and self.re_on_hand[player] == -1:
                    self.re_on_hand[player] = self.ansage[player]
            # is this correct?
            if sum([i == True for i in self.re]) == 2:
                self.re = [True if i == True else False for i in self.re]
                self.re_on_hand = [False if i == False else True for i in self.re_on_hand]
            if sum([i == False for i in self.re]) == 2:
                self.re = [False if i == False else True for i in self.re]
                self.re_on_hand = [True if self.re[i] == True and (self.re_on_hand[i] == -1 or self.re_on_hand[i] == True) else False for i in range(4)]

            if sum([i == True for i in self.re]) == 3 or sum([i == False for i in self.re]) == 3:
                print("only one true re player but not hochzeit")
                breakpoint()

    def possible(self, player, cards):
        """
        check if card is possible on player hand by checking the book
        things that can happen: kreuzdame although not re, color although not, too many cards
        """
        # check with updated player hand if color is needed but not there
        # not trumpf, check color
        for card in cards:
            if card // 100 == 0:
                if not self.colors[player * 4 + card // 10 - 1]:
                    return False
            # trumpf
            else:
                if not self.trumpf[player]:
                    return False
        if self.kreuzdame not in cards and self.re_on_hand[player] == True and not self.hochzeit:
            return False
        if self.kreuzdame in cards and (self.re_on_hand[player] is False or self.re[player] is False):
            return False
        if sum([i == self.kreuzdame for i in cards]) > 1 and not self.hochzeit:
            return False
        return True
