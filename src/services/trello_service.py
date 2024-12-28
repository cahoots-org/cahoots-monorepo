# src/services/trello_service.py
from trello import TrelloClient
from ..utils.config import Config
from ..utils.logger import Logger
from ..models.story import Story

class TrelloService:
    def __init__(self):
        self.config = Config()
        self.logger = Logger("TrelloService")
        self.client = TrelloClient(
            api_key=self.config.trello_api_key,
            api_secret=self.config.trello_api_secret
        )
        
    def create_board(self, name: str) -> object:
        self.logger.info(f"Creating Trello board: {name}")
        board = self.client.add_board(name)
        self.create_default_lists(board)
        return board
        
    def create_default_lists(self, board) -> None:
        board.add_list("Backlog")
        board.add_list("In Progress")
        board.add_list("Review")
        board.add_list("Done")
        
    def add_story_to_board(self, board, story: Story) -> None:
        self.logger.info(f"Adding story to board: {story.title}")
        backlog_list = board.get_list("Backlog")
        backlog_list.add_card(
            name=story.title,
            desc=story.description
        )