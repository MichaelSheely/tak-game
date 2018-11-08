import itertools
import re
# game constants
red = 0
blue = 1
road = 0
wall = 1
capstone = 2
tile_width = 11
kMaximumCarryingCapacity = 5
kInitialBlocks = 14


class PieceCounter(object):
  # works almost like a dictionary, but the values for
  # 'road' and 'wall' are the same, since they use a shared
  # pool of pieces
  def __init__(self, num_caps, num_blocks):
  # def __init__(self):
    self.num_capstones = num_caps
    self.num_road_or_wall_blocks = num_blocks
  def __getitem__(self, key):
    if key == capstone:
      return self.num_capstones
    elif key in [wall, road]:
      return self.num_road_or_wall_blocks
  def __setitem__(self, key, value):
    if key == capstone:
      self.num_capstones = value
    elif key in [wall, road]:
      self.num_road_or_wall_blocks = value
class Player(object):
  def __init__(self, color):
    self.pieces = PieceCounter(num_caps=1, num_blocks=kInitialBlocks)
    # self.pieces = PieceCounter(1, kInitialBlocks)
    # self.pieces = PieceCounter()
    self.color = color


class PlayerIO(object):
  def ParseInput(self, user_input):
    self.action = None
    # move <sep> x <sep> y <sep> direction_to_move <sep> list of drops
    # where sep can be either a space or a comma, sep is optional
    pattern = ('m{sep}{digits}{sep}{digits}{sep}{direction}{sep}'
               '{drop_list}$').format(
                   sep='[ ,]?', digits='(\d+)',
                   direction='([u|d|l|r])', drop_list='([\d+ ,]*)')
    move_match = re.match(pattern, user_input)
    if move_match is not None:
      self.action = 'move'
      self.position = int(move_match.group(1)), int(move_match.group(2))
      self.direction = move_match.group(3)
      self.drop_list = move_match.group(4).replace(',',' ').split(' ')
      # If the user did not enter a drop list, we use the default drop list
      # of [1] (meaning move the top piece just one in the direction indicated
      if self.drop_list == ['']:
        self.drop_list = [1]
      self.drop_list[:] = [int(i) for i in self.drop_list]
      self.spaces_to_move = len(self.drop_list)
      return 
    place_match = re.match('p[ ,]?([r|w|c])[ ,]?(\d+)[ ,]?(\d+)', user_input)
    if place_match is not None:
      self.action = 'place'
      self.pawn_type = {'r': road, 'w': wall, 'c': capstone}[place_match.group(1)]
      self.position = int(place_match.group(2)), int(place_match.group(3))
      return
    if user_input == 'inventory':
      self.game_state.DisplayInventory()
  def VerifyCanMakeMove(self):
    # ensure the player can pick up a piece from here
    if self.game_state.board[self.position].Size() == 0:
      self.errors.append(
          'Tried to move a piece at {} but it was empty'.format(self.position))
      return False
    color_control = self.game_state.board[self.position].ColorControl()
    if color_control != self.game_state.current_player:
      self.errors.append(
          ('Tried to move piece at ({},{}) as {}, but ' +
           ' it is controlled by the other player.').format(
               self.position[0], self.position[1],
               self.game_state.current_player))
      return False
    # next we check if the proposed motion would move us out of bounds
    new_position = Strafe(self.position, self.spaces_to_move, self.direction)
    if not all([0 <= i < self.game_state.board_size for i in new_position]):
      self.errors.append('Moving to the {} by {} would result in a final ' +
                         'position of {}, which is out of bounds'.format(
                             self.direction, self.spaces_to_move, new_position))
      return False
    # now we check that the player can pick up as many pieces as they try to
    if sum(self.drop_list) > self.game_state.board[self.position].Size():
      self.errors.append(('Tried to carry {} pieces from position {}, ' +
                          'but there were only {} pieces there.').format(
                              sum(self.drop_list),
                              self.position,
                              self.game_state.board[self.position].Size()))
      return False
    if sum(self.drop_list) > kMaximumCarryingCapacity:
      self.errors.append(('Tried to carry {} pieces, which is more than the '
                          'maximum carrying capacity of {}.').format(
                              sum(self.drop_list), kMaximumCarryingCapacity))
      return False
    # we also make sure the player doesn't try to skip over any cells
    if any(map(lambda x: x == 0, self.drop_list)):
      self.errors.append(('Tried to skip over a tile without dropping any '
                          'pieces, which is not legal; drop_list: {}').format(
                              self.drop_list))
      return False
    # ensure we don't try to move / drop pieces onto any walls or capstones
    for i, drop in enumerate(self.drop_list):
      new_position = Strafe(self.position, i + 1, self.direction)
      if not self.board[new_position].CanBeCapped():
        # can never move onto a capstone
        if self.board[new_position].Peek().type == capstone:
          self.errors.append('Attempted to drop a piece onto a capstone ' +
                  'at position {}, but capstones cannot be capped'.format(
                      new_position))
          return False
        # in this case we are moving onto a wall, the only way this is ok
        # is if we ourselves are a capstone moving to crush the wall
        idx_in_stack = sum(self.drop_list[:i])
        piece_dropped = self.board[self.position].Peek(idx_in_stack)
        if not piece_dropped.type == capstone:
          self.errors.append(('Attempted to drop {} (originally from stack ' +
              'at {} onto a wall at position {}, but only capstones can ' +
              'crush walls').format(piece_dropped, self.position, new_position))
          return False
    return True
  def IsValidInput(self):
    self.errors = []
    if self.action is None:
      self.errors.append('Could not parse input as a \'place\' or a \'move\'')
      return
    if not all([0 <= i < self.game_state.board_size for i in self.position]):
      self.errors.append('Position {} is out of bounds!'.format(self.position))
    if self.action == 'move':
      self.VerifyCanMakeMove()
    if self.action == 'place':
      if not self.game_state.VerifyCurrentPlayerHasPiece(self.pawn_type):
        self.errors.append('Player is out of {} pieces.'.format(
            Pawn(self.pawn_type, self.game_state.current_player)))
      if self.game_state.board[self.position].Size() > 0:
        self.errors.append('Position {} is not empty! It contains {}'.format(
            self.position, self.game_state.board[self.position]))
    return False if len(self.errors) > 0 else True
  def ScoldUser(self):
      for error in self.errors:
        print(error)
      print('Please try again!')
  def GetValidResponse(self):
    if self.action == 'move':
      return PlayerAction.Move(self.position, self.direction, self.drop_list)
    elif self.action == 'place':
      return PlayerAction.Place(
          self.position, Pawn(self.pawn_type, self.game_state.current_player))
    else:
      raise ValueError('Invalid action: {}'.format(self.action))
  def TryGetMove(self, game_state):
    self.game_state = game_state
    # if the list of drops is ommited, a default of [1] is used
    # (i.e. move just the top piece)
    prompt = ('Place piece \'p [r|w|c] x y\' or ' +
              'move \'m x y u|d|l|r [num_to_drop...]\'? ')
    try:
        self.ParseInput(raw_input(prompt))
    except NameError:
        self.ParseInput(input(prompt))
    if self.IsValidInput():
      return self.GetValidResponse()
    else:
      self.ScoldUser()
      self.game_state.DisplayBoard()
      return None


class PlayerAction(object):
  @staticmethod
  def Move(position, direction, drop_list):
    action = PlayerAction()
    action.type = 'move'
    action.start_position = position
    action.direction = direction
    action.drop_list = drop_list
    return action
  @staticmethod
  def Place(position, pawn):
    action = PlayerAction()
    action.type = 'place'
    action.pawn = pawn
    action.position = position
    return action


class Tile(object):
  def __init__(self):
    self.stack = []
  def ColorControl(self):
    if len(self.stack) == 0:
      return None
    return self.stack[-1].color
  def CanBeCapped(self):
    if len(self.stack) == 0 or self.stack[-1].type = road:
      return True
    else:
      # capstones and walls cannot be capped
      return False
  def Push(self, pawn):
    self.stack.append(pawn)
  def Pop(self):
    return self.stack.pop()
  def Size(self):
    return len(self.stack)
  def Peek(self, i=0):
    if len(self.stack) <= i:
      return None
    return self.stack[-1 - i]
  def __repr__(self):
    stack = []
    for piece in self.stack:
      stack.append(str(piece))
    for i in range(tile_width - len(stack)):
      stack.append(' ')
    return ''.join(stack)

def Colorize(s, color):
  if color == red:
    return '\033[31m{}\033[0m'.format(s)
  if color == blue: 
    return '\033[34m{}\033[0m'.format(s)
  raise ValueError('Unsupported color {}'.format(color))

class Pawn(object):
  def __init__(self, pawn_type, color):
    self.type = pawn_type
    self.color = color
  def __repr__(self):
    if self.type == road:
      return Colorize('|', self.color)
    if self.type == wall:
      return Colorize('-', self.color)
    if self.type == capstone:
      return Colorize('>', self.color)
    raise ValueError('Pawn of type {} and color {} could not be coerced '
                     'to a string!'.format(self.type, self.color))


def Strafe(position, offset, move_direction):
  direction_scalar = 1 if move_direction in ['r', 'd'] else -1
  row, col = position
  if move_direction in ['r', 'l']:
    return row, col + direction_scalar * offset
  else:
    return row + direction_scalar * offset, col



class GameState(object):
  @staticmethod
  def PositionIterator(size):
    return itertools.product(range(size), range(size))
  def GameOver(self):
    return False
  def TileIterator(self):
    class TileIter:
      def __init__(self, board, board_size):
        self.board = board
        self.board_size = board_size
      def iter(self):
        return self.__iter__()
      def __iter__(self):
        self.iter = GameState.PositionIterator(self.board_size)
        return self
      # python 2.x compatibility
      def next(self):
        # raises StopIteration will bubble up when we're done iterating
        position = self.iter.next()
        tile = self.board[position]
        return position, tile
      def __next__(self):
        # raises StopIteration will bubble up when we're done iterating
        position = self.iter.__next__()
        tile = self.board[position]
        return position, tile
    return TileIter(self.board, self.board_size)
  def CreateBoard(self, size):
    self.board_size = size
    self.board = {(r, c) : Tile() for (r, c) in GameState.PositionIterator(size)}
  def DisplayBoard(self):
    display = []
    for pos, tile in self.TileIterator():
      if pos[1] == 0:
        display.append('\n' + '#' * (tile_width + 2) * self.board_size)
        for _ in range(4):
          display.append('\n')
          for _ in range(self.board_size):
            display.append(' ' * tile_width + '##')
        display.append('\n')
      display.append(str(tile))
      display.append('##')
    print(''.join(display))
  def DisplayInventory(self):
      print('Player has {} capstones and {} wall / road pieces'.format(
          self.players[self.current_player].pieces[capstone],
          self.players[self.current_player].pieces[wall + road]))
  def GetMove(self):
    while True:
      move = PlayerIO().TryGetMove(self)
      if move is not None:
        return move
  def VerifyCurrentPlayerHasPiece(self, pawn_type):
    if self.players[self.current_player].pieces[pawn_type] == 0:
      return False
    return True
  def Execute(self, player_action):
    if player_action.type == 'move':
      move_direction = player_action.direction
      start_position = player_action.start_position
      pieces_to_pick_up = sum(player_action.drop_list)
      carried_pieces = []
      for _ in range(pieces_to_pick_up):
        carried_pieces.append(self.board[start_position].Pop())
      print(carried_pieces)
      for offset, deposit in enumerate(player_action.drop_list):
        position = Strafe(start_position, offset + 1, move_direction)
        print('placing at {}'.format(position))
        for _ in range(deposit):
          self.board[position].Push(carried_pieces.pop())
    if player_action.type == 'place':
      self.board[player_action.position].Push(player_action.pawn)
      if player_action.pawn.type == capstone:
        self.players[self.current_player].pieces[capstone] -= 1
      else:
        # these draw from the same bank of pieces
        self.players[self.current_player].pieces[wall] -= 1
        self.players[self.current_player].pieces[road] -= 1
  def TakeTurn(self):
    self.DisplayBoard()
    player_action = self.GetMove()
    self.Execute(player_action)
    self.EndTurn()
  def EndTurn(self):
    self.current_player = self.next_player 
    if self.turn_counter == 1:
      self.next_player = self.current_player
    elif self.next_player == red:
      self.next_player = blue
    else:
      self.next_player = red


def NewGame(board_size=5):
  game_state = GameState()
  game_state.CreateBoard(board_size)
  game_state.current_player = red
  game_state.next_player = blue
  game_state.turn_counter = 0
  game_state.players = {color: Player(color) for color in [red, blue]}
  return game_state


def start_game():
  game = NewGame()
  while not game.GameOver():
    game.TakeTurn()

start_game()
