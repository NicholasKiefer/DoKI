# This is a very simple Python 3 implementation of the Information Set Monte Carlo Tree Search algorithm.
# The function ISMCTS(rootstate, itermax, verbose = False) is towards the bottom of the code.
# It aims to have the clearest and simplest possible code, and for the sake of clarity, the code
# is orders of magnitude less efficient than it could be made, particularly by using a
# state.GetRandomMove() or state.DoRandomRollout() function.
#
# An example GameState classes for Knockout Whist is included to give some idea of how you
# can write your own GameState to use ISMCTS in your hidden information game.
#
# Written by Peter Cowling, Edward Powley, Daniel Whitehouse (University of York, UK) September 2012 - August 2013.
#
# Licence is granted to freely use and distribute for any sensible/legal purpose so long as this comment
# remains in any distributed code.
#
# For more information about Monte Carlo Tree Search check out our web site at www.mcts.ai
# Also read the article accompanying this code at ***URL HERE***
from tqdm import tqdm
from math import sqrt, log
import random
from doko_game.doko import Doko, Book
from copy import deepcopy
import numpy as np
from itertools import accumulate
import time


class GameState:
    """ A state of the game, i.e. the game board. These are the only functions which are
        absolutely necessary to implement ISMCTS in any imperfect information game,
        although they could be enhanced and made quicker, for example by using a
        GetRandomMove() function to generate a random move during rollout.
        By convention the players are numbered 1, 2, ..., self.numberOfPlayers.
    """

    def __init__(self, number_of_players, player_to_move):
        self.numberOfPlayers = number_of_players
        self.playerToMove = player_to_move

    def GetNextPlayer(self, p):
        """ Return the player to the left of the specified player
        """
        pass

    def CloneAndRandomize(self, observer):
        """ Create a deep clone of this game state, randomizing any information not visible to the specified
         observer player.
        """
        pass

    def DoMove(self, move):
        """ Update a state by carrying out the given move.
            Must update playerToMove.
        """
        # self.playerToMove = self.GetNextPlayer(self.playerToMove)
        pass

    def GetMoves(self):
        """ Get all possible moves from this state.
        """
        pass

    def GetResult(self, player):
        """ Get the game result from the viewpoint of player.
        """
        pass

    def __repr__(self):
        """ Don't need this - but good style.
        """
        pass


class Doko_ISMCTS(GameState):
    def __init__(self):
        super().__init__(4, 0)
        self.realdoko = Doko(123)
        # self.realdoko.reset()
        self.playerToMove = self.realdoko.player_to_play

    def CloneAndRandomize(self, observer):
        """ Create a deep clone of this game state, randomizing any information not visible to the specified
         observer player.
         playerToMove = observer ; always
         oke, now it gets weird, we need to actually INFER how many cards every player has
         and then give accordingly...
        """
        xb = self.realdoko.book
        x = self.realdoko
        st = Doko_ISMCTS()
        st.playerToMove = observer
        keep_hand = list(self.realdoko.hands[st.playerToMove])

        # give back to players, with outside observer + observer info
        tmp_book = Book(list(xb.trumpf), list(xb.ansage),
                        list(xb.re_on_hand), list(xb.re), xb.hochzeit, xb.solo, list(xb.colors))
        # re_on_hand, if != -1, leave alone, if == -1 lookup observer by hand, if in game, should handle itself
        # re_on_hand should also turn False for kontra, safety reason
        if not tmp_book.hochzeit:
            if tmp_book.re_on_hand[observer] == -1:
                tmp_book.re_on_hand[observer] = True if st.realdoko.kreuzdame in keep_hand else False
            if tmp_book.re[observer] == -1:
                tmp_book.re[observer] = tmp_book.re_on_hand[observer]
            tmp_book.infer_team_update()

        st.realdoko = Doko(123, x.player_to_play, x.previous_player, x.card_number, x.bedien, list(x.game),
                           list(x.haufen), x.abfrage, list(x.doppelkopf), list(x.karlchen), list(x.fuchs))
        st.realdoko.book = Book(list(xb.trumpf), list(xb.ansage),
                                list(xb.re_on_hand), list(xb.re), xb.hochzeit, xb.solo, list(xb.colors))

        st.realdoko.hands = [[], [], [], []]
        st.realdoko.hands[st.playerToMove] = keep_hand

        # find out which cards are not on observers hand and in game
        full_deck = list(self.realdoko.all_cards)
        for i in list(self.realdoko.game + keep_hand):
            if i != 0:
                for idx, f in enumerate(full_deck):
                    if f == i:
                        full_deck[idx] = 0
                        break
        left_over = [i for i in full_deck if i != 0]

        # regive cards
        players = set(range(4)) - {observer}
        # hand_lens: 12 - #full_stichs - extra card if already played
        gamelen = len([i for i in self.realdoko.game if i != 0])
        full_stichs = gamelen // 4
        hand_lens = [12 - full_stichs for _ in range(4)]
        # we can go back in stich because of consistency
        # 2 cards in stich: player_to_play - 1 and player_to_play - 2 have one less
        cards_in_stich = gamelen % 4
        for i in range(1, cards_in_stich + 1):
            hand_lens[(observer - i) % 4] -= 1
        hand_lens = [i for idx, i in enumerate(hand_lens) if idx != observer]
        hand_slices = list(accumulate(hand_lens, initial=0))
        flag = False
        count = 0
        while True:
            count += 1
            random.shuffle(left_over)
            for idx, player in enumerate(players):
                if not tmp_book.possible(player, left_over[hand_slices[idx]:hand_slices[idx + 1]]):
                    break  # escape for loop and repeat
                if idx == 2:
                    flag = True
            if flag:  # escape while
                break
            if count > 100000:
                breakpoint()
        for idx, player in enumerate(players):
            hand = left_over[hand_slices[idx]:hand_slices[idx + 1]]
            st.realdoko.hands[player] = hand
        # fill up to 12
        st.realdoko.hands = [i + [0] * (12 - len(i)) for i in st.realdoko.hands]
        return st

    def DoMove(self, move):
        """ Update a state by carrying out the given move.
            Must update playerToMove.
        """
        # todo: move is now direct order, don't pickup from hand anymore, that's stupid
        observation, reward, done = self.realdoko.step(move)
        self.playerToMove = self.realdoko.player_to_play
        return reward

    def GetMoves(self):
        """ Get all possible moves from this state.
        do we accidently consider same moves to be different, because of length in self.realdoko.legal_actions
        they look different here, but not in self.realdoko.hands[player][actions]
        """
        # todo: just return set(hand) - {0} or {12, 13}
        ret = self.realdoko.legal_actions()
        if 13 not in ret:
            # filter actions
            ret = list({self.realdoko.hands[self.realdoko.player_to_play][i]: i for i in ret}.values())
        return ret

    def GetResult(self, player):
        """ Get the game result from the viewpoint of player.
        """
        if self.realdoko.done:
            result = self.realdoko.calculate_reward()
            result = result[player]
        else:
            result = 0
        return result


class Node:
    """ A node in the game tree. Note wins is always from the viewpoint of playerJustMoved.
    """

    def __add__(self, other):
        """
        this is a superficial add: only visit of direct children get added together, everything else is dropped
        """
        assert self.move == other.move
        assert self.parentNode == other.parentNode
        assert self.playerJustMoved == other.playerJustMoved
        new_node = Node()
        new_node.move = self.move
        new_node.parentNode = self.parentNode
        children = []
        for node in self.childNodes:
            visits = node.visits
            wins = node.wins
            for otherchild in other.childNodes:
                if otherchild.move == node.move:
                    visits += otherchild.visits
                    wins += otherchild.wins
            node.visits = visits
            node.wins = wins
            children.append(node)
        new_node.childNodes = children
        return new_node

    def __init__(self, move=None, parent=None, player_just_moved=None):
        self.move = move  # the move that got us to this node - "None" for the root node
        self.parentNode = parent  # "None" for the root node
        self.childNodes = []
        self.wins = 0
        self.visits = 0
        self.avails = 1
        self.playerJustMoved = player_just_moved  # the only part of the state that the Node needs later, None root

    def get_untried_moves(self, legal_moves):
        """ Return the elements of legalMoves for which this node does not have children.
        """

        # Find all moves for which this node *does* have children
        triedMoves = [child.move for child in self.childNodes]

        # Return all moves that are legal but have not been tried yet
        return [move for move in legal_moves if move not in triedMoves]

    def ucb_select_child(self, legal_moves, exploration=0.2):
        """ Use the UCB1 formula to select a child node, filtered by the given list of legal moves.
            exploration is a constant balancing between exploitation and exploration, with default value 0.7
            (approximately sqrt(2) / 2)
        """

        # Filter the list of children by the list of legal moves
        legalChildren = [child for child in self.childNodes if child.move in legal_moves]

        # Get the child with the highest UCB score
        s = max(
            legalChildren,
            key=lambda c:
            # wins / visits + 0.7 * avails / visits
            float(c.wins) / float(c.visits) + exploration * sqrt(log(c.avails) / float(c.visits)),
        )

        # Update availability counts -- it is easier to do this now than during backpropagation
        for child in legalChildren:
            child.avails += 1

        # Return the child selected above
        return s

    def add_child(self, m, p):
        """ Add a new child node for the move m.
            Return the added child node
        """
        n = Node(move=m, parent=self, player_just_moved=p)
        self.childNodes.append(n)
        return n

    def update(self, terminal_state):
        """ Update this node - increment the visit count by one, and increase the win count by the result of
        terminalState for self.playerJustMoved.
        """
        self.visits += 1
        if self.playerJustMoved is not None:
            self.wins += terminal_state.GetResult(self.playerJustMoved)


def ismcts(rootstate: Doko_ISMCTS, itermax, verbose=False):
    """ Conduct an ISMCTS search for itermax iterations starting from rootstate.
        Return the best move from the rootstate.

        For STOP, the search speed in simulations per second is
        measured, and in regular intervals (e.g. 50 rollouts) it is
        checked how many rollouts are still expected in the remainder
        of the total planned search time. If the number of simulations
        required for the second-most-visited move at the root to catch
        up to the most-visited one exceeds this expected number of
        remaining simulations, the search can safely be terminated
        without changing the final outcome.

        n * timeleftn / timespentn * 1 < visitsbestn − visitssecondbestn
    """
    rootnode = Node()

    # itermax = int(0.1 * itermax) if rootstate.realdoko.card_number >= 40 else itermax
    # itermax = max(1, itermax)
    # states = [rootstate.CloneAndRandomize(rootstate.playerToMove) for _ in range(itermax)]
    begin = time.time()
    start = time.time()
    for idx in range(1, itermax + 1):
        if idx % 50 == 0:
            process_time = time.time() - start
            timeleft = (itermax - idx - 1) * process_time / 50
            timespent = time.time() - begin
            visits = sorted(rootnode.childNodes, key=lambda c: c.visits, reverse=True)
            if idx * timeleft / timespent < visits[0].visits - visits[1].visits:
                # impossible for second option to gain on first, therefore early exit
                break
            start = time.time()

        node = rootnode
        # Determinize
        state = rootstate.CloneAndRandomize(rootstate.playerToMove)
        # state = states[idx]

        # Select
        # while state has moves AND untried moves of node! are empty, move to next state
        if len(state.GetMoves()) == 1:
            node.add_child(state.GetMoves()[0], state.playerToMove)
            break
        while state.GetMoves() != [] and node.get_untried_moves(state.GetMoves()) == []:
            # node is fully expanded and non-terminal
            node = node.ucb_select_child(state.GetMoves())
            state.DoMove(node.move)

        # Expand
        untriedMoves = node.get_untried_moves(state.GetMoves())
        if untriedMoves:  # if we can expand (i.e. state/node is non-terminal)
            # todo: here we can do better probably
            m = random.choice(untriedMoves)
            player = state.playerToMove
            state.DoMove(m)
            node = node.add_child(m, player)  # add child and descend tree

        # Simulate
        while state.GetMoves():  # while state is non-terminal
            # todo: here we can do better again
            state.DoMove(random.choice(state.GetMoves()))

        # backpropagate from the expanded node and work back to the root node
        while node is not None:
            node.update(state)
            node = node.parentNode

    # return the move that was most visited
    return max(rootnode.childNodes, key=lambda c: c.visits).move, rootnode


def play_game(agents):
    """ Play a sample game between ISMCTS players.
    """
    state = Doko_ISMCTS()
    state.realdoko.reset()
    state.playerToMove = state.realdoko.player_to_play
    while state.GetMoves():
        search_state = deepcopy(state)  # todo: need to do this? because state gets changed in agent call
        # multiprocess this, faster by * processes?
        m, rootnode = ismcts(search_state, agents[state.playerToMove], )
        state.DoMove(m)
    reward = state.realdoko.calculate_reward()
    return reward


if __name__ == "__main__":
    smart_agents = {
        0: 100,
        1: 10,
        2: 10,
        3: 10,
    }
    results = np.array([0, 0, 0, 0])
    try:
        for _ in tqdm(range(10), desc="playing games"):
            one_game = play_game(smart_agents)
            results += np.array(one_game)
    except KeyboardInterrupt:
        pass
    print(results)
