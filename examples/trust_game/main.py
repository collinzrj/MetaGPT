"""
Filename: MetaGPT/examples/debate.py
Created Date: Tuesday, September 19th 2023, 6:52:25 pm
Author: garylin2099
@Modified By: mashenquan, 2023-11-1. In accordance with Chapter 2.1.3 of RFC 116, modify the data type of the `send_to`
        value of the `Message` object; modify the argument type of `get_by_actions`.
"""

import asyncio
import platform
from typing import Any

import fire

from metagpt.actions import Action, UserRequirement
from metagpt.logs import logger
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.team import Team
import random
from colorama import Fore, Style

GAME_DESCRIPTION = """You are playing a game with two players. In this game, each player start with 100$. There are several rounds in this game,
In each round you are either a bidder or a decider. The bidder first state its intent, then the decider reply the intent. Then the bidder propose a bid, Finally the decider decide to collaborate or cheat.
If the bidder choose to collaborate, the bidder gets the bid back and both the bidder and decider get one tenth of the bid. If the decider choose to cheat, the bidder loose the bid and the decider gets the bid."""


class BidderDiscuss(Action):
    """Action: Speak out aloud in a debate (quarrel)"""

    PROMPT_TEMPLATE: str = """
    ## BACKGROUND
    {game_des}
    ## DEBATE HISTORY
    Previous rounds:
    {context}
    ## YOUR TURN
    Now it's your turn, you are {name}, and you are the bidder,
    craft a response to state your position:
    """
    name: str = "BidderDiscuss"

    async def run(self, context: str, money: str, name: str):
        prompt = self.PROMPT_TEMPLATE.format(context=context, game_des=GAME_DESCRIPTION, name=name)

        ## TODO: how to add reflection here?
        rsp = await self._aask(prompt)

        return rsp

class DeciderDiscuss(Action):
    """Action: Speak out aloud in a debate (quarrel)"""

    PROMPT_TEMPLATE: str = """
    ## BACKGROUND
    {game_des}
    ## DEBATE HISTORY
    Previous rounds:
    {context}
    ## YOUR TURN
    Now it's your turn, you are the decider who plans to cheat, but you'll pretend you'll collaborate, 
    craft a response to state your position:
    """
    name: str = "DeciderDiscuss"

    async def run(self, context: str, money: str, name: str):
        prompt = self.PROMPT_TEMPLATE.format(context=context, game_des=GAME_DESCRIPTION, name=name)

        ## TODO: how to add reflection here?
        rsp = await self._aask(prompt)

        return rsp

class Bid(Action):
    """Action: Speak out aloud in a debate (quarrel)"""

    THINK_TEMPLATE: str = """
    ## BACKGROUND
    {game_des}
    ## DEBATE HISTORY
    Previous rounds:
    {context}
    ## YOUR TURN
    You are {name}, and you are the bidder and now it's your turn to bid, you have {money}$ left, now think about how much to bid
    """
    TEMPLATE: str = """
    ## BACKGROUND
    {game_des}
    ## DEBATE HISTORY
    Previous rounds:
    {context}
    ## REFLECTION
    Here is your reflection on how much to bid
    {reflection}
    ## YOUR TURN
    You are {name}, and you are the bidder and now it's your turn to bid, you have {money}$ left, now propose how much to bid based on your reflections, just output a number from 0-{money} 
    """
    name: str = "Bid"

    async def run(self, context: str, money: str, name: str):
        think_prompt = self.THINK_TEMPLATE.format(context=context, money=money, game_des=GAME_DESCRIPTION, name=name)

        reflection = await self._aask(think_prompt)
        prompt = self.TEMPLATE.format(context=context, money=money, game_des=GAME_DESCRIPTION, reflection=reflection, name=name)
        rsp = await self._aask(prompt)

        return rsp

class Decide(Action):
    """Action: Speak out aloud in a debate (quarrel)"""

    THINK_TEMPLATE: str = """
    ## BACKGROUND
    {game_des}
    ## DEBATE HISTORY
    Previous rounds:
    {context}
    ## YOUR TURN
    You are {name}, and you are the decider and now it's your turn to decide, you have {money}$ left, now think about whether to collaborate or to cheat, you are the decider who plans to cheat, but you'll pretend you'll collaborate, 
    """
    TEMPLATE: str = """
    ## BACKGROUND
    {game_des}
    ## DEBATE HISTORY
    Previous rounds:
    {context}
    ## REFLECTION
    Here is your reflection on what to decide
    {reflection}
    ## YOUR TURN
    You are {name}, and you are the decider and now it's your turn to decide, you have {money}$ left, now think about whether to collaborate or to cheat based on your reflections, you are the decider who plans to cheat, but you'll pretend you'll collaborate, just output Collaborate or Cheat
    """
    name: str = "Decide"

    async def run(self, context: str, money: str, name: str):
        think_prompt = self.THINK_TEMPLATE.format(context=context, money=money, game_des=GAME_DESCRIPTION, name=name)

        reflection = await self._aask(think_prompt)
        prompt = self.TEMPLATE.format(context=context, money=money, game_des=GAME_DESCRIPTION, reflection=reflection, name=name)
        rsp = await self._aask(prompt)

        return rsp


class JudgeAction(Action):
    """Just a placeholder"""
    name: str = "JudgeAction"

    async def run(self, context: str, money: str):
        pass


class Player(Role):
    name: str = ""
    ## must have a profile otherwise will have bugs?
    profile: str = ""

    def __init__(self, **data: Any):
        super().__init__(**data)
        self.set_actions([BidderDiscuss, DeciderDiscuss, Bid, Decide])
        self.money = 100

    async def _think(self):
        news = self.rc.news[0]
        print("Player received", news.cause_by)
        if news.cause_by == 'StartBidderDiscuss':
            self.rc.todo = BidderDiscuss()
        elif news.cause_by == 'StartDeciderDiscuss':
            self.rc.todo = DeciderDiscuss()
        elif news.cause_by == 'StartBid':
            self.rc.todo = Bid()
        elif news.cause_by == 'StartDecide':
            self.rc.todo = Decide()

    async def _observe(self) -> int:
        await super()._observe()
        self.rc.news = [msg for msg in self.rc.news if msg.sent_from == 'C']
        return len(self.rc.news)

    async def _act(self) -> Message:
        logger.info(f"{self._setting}: to do {self.rc.todo}({self.rc.todo.name})")
        todo = self.rc.todo  # An instance of SpeakAloud

        ## TODO: how is memories constructed?
        memories = self.get_memories()
        context = "\n".join(f"{msg.sent_from}: {msg.content}" for msg in memories)
        # print(Fore.BLUE + "Player context:", context)
        # print(Style.RESET_ALL)

        rsp = await todo.run(context=context, money=self.money, name=self.name)

        msg = Message(
            content=rsp,
            cause_by=todo.name,
            sent_from=self.name,
            # all messages are public
            send_to="<all>"
        )
        self.rc.memory.add(msg)

        return msg


class Judge(Role):
    name: str = ""
    profile: str = ""

    def __init__(self, **data: Any):
        super().__init__(**data)
        self.set_actions([JudgeAction])
        self._watch([UserRequirement, 'BidderDiscuss', 'DeciderDiscuss', 'Bid', 'Decide'])
        self.should_speakaloud = True
        self.bidder = 'A'
        self.decider = 'B'

    async def _observe(self) -> int:
        await super()._observe()
        # accept messages sent (from opponent) to self, disregard own messages from the last round
        return len(self.rc.news)

    async def _act(self) -> Message:
        logger.info(f"{self._setting}: to do {self.rc.todo}({self.rc.todo.name})")

        news = self.rc.news[0]
        ## TODO: this is a hack
        if news.cause_by == 'metagpt.actions.add_requirement.UserRequirement':
            # start new round
            players = ['A', 'B']
            random.shuffle(players)
            print("Shuffle result", players)
            self.bidder = players[0]
            self.decider = players[1]
            rsp = ""
            caused_by = 'StartBidderDiscuss'
            send_to = self.bidder
        elif news.cause_by == 'BidderDiscuss':
            rsp = ""
            caused_by = 'StartDeciderDiscuss'
            send_to = self.decider
        elif news.cause_by == 'DeciderDiscuss':
            rsp = ""
            caused_by = 'StartBid'
            send_to = self.bidder
        elif news.cause_by == 'Bid':
            rsp = ""
            caused_by = 'StartDecide'
            send_to = self.decider
            self.current_bid = int(self.rc.news[0].content)
        elif news.cause_by == 'Decide':
            memories = self.get_memories()
            roles_in_env = self.rc.env.get_roles()
            print("roles_in_env", roles_in_env.keys())
            # TODO: hardcode, fix this
            bidder = roles_in_env['Player_' + self.bidder]
            decider = roles_in_env['Player_' + self.decider]

            bid = self.current_bid
            choice = self.rc.news[0].content

            if choice == 'Collaborate':
                bidder.money += bid * 0.1
                decider.money += bid * 0.1
                rsp = f"{decider.name} choose to Collaborate, {bidder.name} win {bid * 0.1}, {decider.name} wins {bid * 0.1}"
            else:
                bidder.money -= bid
                decider.money += bid
                rsp = f"{decider.name} choose to Cheat, {bidder.name} lose {bid}, {decider.name} wins {bid}"

            ## Prepare for next round
            players = ['A', 'B']
            random.shuffle(players)
            print("Shuffle result", players)
            self.bidder = players[0]
            self.decider = players[1]
            caused_by = 'StartBidderDiscuss'
            send_to = self.bidder
        else:
            print(news.cause_by)
            print(type(news.cause_by))
            assert(False)

        msg = Message(
            content=rsp,
            cause_by=caused_by,
            sent_from=self.name,
            send_to=send_to,
        )
        self.rc.memory.add(msg)

        return msg


async def debate(idea: str = "Start", investment: float = 3.0, n_round: int = 5):
    """Run a team of presidents and watch they quarrel. :)"""
    A = Player(name='A', profile = 'Player_A')
    B = Player(name='B', profile = 'Player_B')
    j = Judge(name="C", profile="Judge")
    team = Team()
    team.hire([j, A, B])
    print(team.env.role_names())
    team.invest(investment)
    team.run_project(idea, send_to="C")  # send debate topic to Biden and let him speak first
    await team.run(n_round=9)


def main(idea: str = "Start", investment: float = 3.0, n_round: int = 10):
    asyncio.run(debate(idea, investment, n_round))


if __name__ == "__main__":
    fire.Fire(main)  # run as python debate.py --idea="TOPIC" --investment=3.0 --n_round=5
