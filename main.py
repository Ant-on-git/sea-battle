"""
В след. версии:
    - логика компьютера при отсутствии подбитых клеток
    - возможность выбора размера поля и количества кораблей
"""

from random import randint, choice
from time import sleep


class SeaBattleExceptions(Exception):
    def __init__(self, *args):
        self.message = args[0] if args else None

    def __str__(self):
        return f'Ошибка: {self.message}'


class BoardOutException(SeaBattleExceptions): pass


class ShipNextToAnotherException(SeaBattleExceptions): pass


class AlredyShootException(SeaBattleExceptions): pass


class Dot:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.value = ' '

    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        else:
            return self.value == other.value

    def __str__(self):
        res = self.value if isinstance(self.value, str) else str(self.value)
        return res


class Ship:
    def __init__(self, lenght, start, direction):
        self.lenght = lenght
        self.start = start
        self.direction = direction  # 1 = right || -1 = left || 6 = down || -6 = up
        self.health = lenght
        self.ship_dots = [(self.start + self.direction * l) for l in range(self.lenght)]
        self.around_ship_dots = []

    def __str__(self):
        return '■'


class Board:
    def __init__(self, hide, all_ships):
        self.hide = hide
        self.ships_left = {}
        self.all_ships = all_ships
        self.dots = [Dot(n//6, n%6) for n in range(36)]

    def __iter__(self):
        self.ind = 0
        return self

    def __next__(self):
        if self.ind < len(self.dots):
            res = self[self.ind]
            self.ind += 1
            return res
        else:
            raise StopIteration

    def __getitem__(self, item):
        return self.dots[item].value

    def __setitem__(self, key, value):
        self.dots[key].value = value

    def add_ship(self, start, lenght, direction):
        ''' проверяет возможность размещения корабля. если можно поставить -
        соответствующим клеткам присваивается ссылка на этот корабль '''
        ship = Ship(lenght, start, direction)
        position = ship.ship_dots
        dots_around_ship = []
        try:
            if not(0 <= start <= 35) or not(0 <= start + direction*(lenght-1) <= 35) or \
            direction in (-1, 1) and len(set(map(lambda x: x // 6, position))) != 1:  # пров. распол. на 1 строке
                raise BoardOutException('Корабль не помещается на поле')
        except Exception as e:
            return False, e

        skip_ind = []  # чтобы пропускать палубы собственого корабля при проверке в contur
        for coord in position:
            try:
                dots_around_coord = self.countur(coord, skip_ind=skip_ind)
            except ShipNextToAnotherException as e:
                return False, e
            skip_ind.append(coord)
            dots_around_ship.extend(dots_around_coord)

        # добавляем корабль в базу и меняем точки поля и возвращаем список точек вокруг корабля:
        if lenght in self.ships_left:
            self.ships_left[lenght] += 1
        else:
            self.ships_left[lenght] = 1
        ship.around_ship_dots = set(dots_around_ship) -set(skip_ind)
        for ind in ship.ship_dots:
            self.dots[ind].value = ship
        return True, (ship.around_ship_dots | set(ship.ship_dots))

    def clear(self): self.dots = [Dot(n // 6, n % 6) for n in range(36)]

    def countur(self, coord, skip_ind=[], call_from=''):
        ''' проверяем соседние клетки на занятость.
        если не заняты - возвращаем список клеток вокруг. вызов из add_ship и ai_ask  '''
        around_dots = []
        for i in [-1, 0, 1]:
            for j in [-6, 0, 6]:
                if (coord + i + j) in skip_ind:
                    continue
                if (coord + i + j) % 6 not in (coord%6 - 1, coord%6, coord%6 + 1) or not (0 <= coord + i + j <= 35):
                    continue
                if i == j == 0:
                    continue
                if isinstance(self[coord + i + j], Ship) and not call_from:
                    raise ShipNextToAnotherException('Корабль нельзя поставить, т.к. клетка рядом занята')
                elif call_from == 'ai_ask':
                    around_dots.append(coord + i + j)
                around_dots.append(coord + i + j)
        return around_dots

    def out(self, coord):
        return 0 <= coord <= 35

    def shot(self, coord):
        if self[coord] in ('x', 'X', '.'):
            raise AlredyShootException('Сюда ужк стреляли')
        if not(0 <= coord <= 35):
            raise BoardOutException('Нельзя стрелять за пределы поля')
        if isinstance(self[coord], Ship):
            if self[coord].health > 1:
                self[coord].health -= 1
                self[coord] = 'x'
            else:
                self.ships_left[self[coord].lenght] -= 1
                for around_cell in self[coord].around_ship_dots:
                    self[around_cell] = '.'
                for ship_cell in self[coord].ship_dots:
                    self[ship_cell] = 'X'
            return True

        self[coord] = '.'
        return False


class Player:
    def __init__(self, my_board, enemy_board):
        self.my_board = my_board
        self.enemy_board = enemy_board

    def ask(self): pass

    def move(self):
        try:
            coord = self.ask()
            hit = self.enemy_board.shot(coord)
        except Exception as e:
            print(e)
            return 'exception'
        return hit


class User(Player):
    def ask(self):
        while True:
            x, y = map(int, input('Введите две координаты через пробел: ').split())
            coord = (x-1)*6 + (y-1)
            if not (1 <= x <= 6) or not (1 <= y <= 6):
                raise BoardOutException('Выстрел за пределы поля')
            return coord


class AI(Player):
    def ask(self):
        '''
        логика ходов компьютера.
        1) Есть две подбитых клетки рядом - определяем направление корабля, идем по направлению,
            пока не найдем пустую клетку (в обоих направленях), выбираем из этих пустых клеток
        2)Есть только одна подбитая клетка, определяем соседние ячейки, выбираем пустые и стреляем
        3) Нет подбитых - бъем рандомом
        '''
        enemy_field = []
        for cell in self.enemy_board:
            if str(cell) in '.xX ':
                enemy_field.append(str(cell))
            else:
                enemy_field.append(' ')

        shot_coord_list = []
        if 'x' in enemy_field:
            ind_x = enemy_field.index('x')
            around_dots = {enemy_field[ind]: ind for ind in self.enemy_board.countur(ind_x, call_from='ai_ask') \
                           if ind % 6 == ind_x % 6 or ind // 6 == ind_x // 6}
            if 'x' in around_dots.keys():
                direction = abs(ind_x - around_dots['x'])
                for n in (1, -1):
                    direction *= n
                    coord = ind_x
                    while True:
                        coord += direction
                        if not(0 <= coord <= 35) or (direction==1 and coord%6 < ind_x%6) or (direction==-1 and coord%6 > ind_x%6):
                            break
                        if enemy_field[coord] == '.':
                            break
                        elif enemy_field[coord] == 'x':
                            continue
                        else:
                            shot_coord_list.append(coord)
                            break
            if shot_coord_list:
                ai_shot = choice(shot_coord_list)
                sleep(1)
                print('Ход компьютера:', (ai_shot // 6) + 1, (ai_shot % 6) + 1)
                return ai_shot

            ai_shot = around_dots[' ']
            sleep(1)
            print('Ход компьютера:', (ai_shot // 6) + 1, (ai_shot % 6) + 1)
            return ai_shot

        else:
            shot_coord_list = [ind for ind, v in enumerate(enemy_field) if v == ' ']  # пока так. потом дописать логику нахождения вероятностей
            ai_shot = choice(shot_coord_list)
            sleep(1)
            print('Ход компьютера:', (ai_shot // 6) + 1, (ai_shot % 6) + 1)
            return ai_shot


class Game:
    def __init__(self, ships={}):
        user_board = Board(hide=False, all_ships=ships)
        ai_board = Board(hide=True, all_ships=ships)
        self.user_board = user_board
        self.ai_board = ai_board
        self.user = User(user_board, ai_board)
        self.ai = AI(ai_board, user_board)

    def random_board(self):
        def gen_ships(board):
            ships_to_add = self.user_board.all_ships.copy()
            while any(ships_to_add.values()):
                count = 0
                ships_to_add = board.all_ships.copy()
                board.ships_left = {}
                board.clear()
                free_space = [i for i in range(36)]
                for lenght, numbers in ships_to_add.items():
                    while numbers and count < 1000:
                        added, around_dots = board.add_ship(choice(free_space), lenght, choice((-1, 1, -6, 6)))
                        count += 1
                        if added:
                            ships_to_add[lenght] -= 1
                            numbers -= 1
                            for ind in around_dots:
                                free_space.remove(ind) if ind in free_space else ''
                                if not free_space:
                                    break
                        if not free_space:
                            break
        gen_ships(self.user_board)
        gen_ships(self.ai_board)

    def print_fields(self):
        def strings_gen(field):
            clear = '\033[0m'  # очистить цвета
            bf = '\033[40m'    # черный фон
            yield ('\033[4m   | 1 | 2 | 3 | 4 | 5 | 6 |\033[0m')
            for i in range(6):
                string = f'{i + 1}  |'
                for j in range(6):
                    cell = str(field[i * 6 + j])
                    if cell == '■' and field.hide:
                        cell = ' '
                    col = '\033[31m' if cell in 'xX' else '\033[32m' if cell == '■' else '\033[33m'
                    string += f'{bf} {col}{cell}{clear}{bf} |{clear}'
                yield string
        user_strings = strings_gen(self.user_board)
        ai_strings = strings_gen(self.ai_board)
        print('            ИГРОК:                               Компьютер:      ')
        for user, comp in zip(user_strings, ai_strings):
            print(user + '          ' + comp)

    def greet(self):
        print("\033[33mДобро пожаловать в МОРСКОЙ БОЙ!")
        sleep(1)
        print("Размер поля: 6 на 6")
        print('Состав кораблей: 1 (3 палубы), 2 (2 палубы), 4 (1 палуба).')
        sleep(2)
        print("Игра с компьютером. Корабли расставляются случайно.")
        sleep(1)
        print("Для выстрела нужно ввести 2 координаты X и Y через пробел.")
        print('Координаты должны соответствовать указанным на поле номерам строк и столбцов.')
        sleep(1)
        print("Выиграл тот, кто подбил все вражеские корабли.")
        print("УДАЧИ, ВОИН!\033[0m")
        sleep(2)

    def loop(self):
        winner = False
        first_step = randint(0, 1)  # 0 - комп, 1 - игрок
        steps = (1, 0) if first_step else (0, 1)
        while not winner:
            for step in steps:
                print()
                if step == 0:
                    col = '\033[32m'
                    clear = '\033[0m'
                    message = f'{col}- - - - - - - - - - - - - ХОДИТ ИГРОК - - - - - - - - - - - - - -{clear}'
                    move_func = self.user.move
                    enemy_ships_left_values = self.ai_board.ships_left.values
                    win_message = f"{col}! ! ! ! ! ! ! ! ! Вы победили, Поздравляем ! ! ! ! ! ! ! ! ! ! ! {clear}"
                else:
                    col = '\033[31m'
                    clear = '\033[0m'
                    message = f'{col}- - - - - - - - - - - ХОДИТ КОМПЬЮТЕР - - - - - - - - - - - - - -{clear}'
                    move_func = self.ai.move
                    enemy_ships_left_values = self.user_board.ships_left.values
                    win_message = f"{col}! ! ! ! ! ! ! ! ! ! ! ! Вы проиграли ! ! ! ! ! ! ! ! ! ! ! ! ! !{clear}"

                print(col, message, clear)
                while True:
                    print(col, end='')
                    move = move_func()
                    print(clear, end='')
                    self.print_fields()
                    print()
                    if move == 'exception':
                        continue
                    if not move:
                        break
                    if not any(enemy_ships_left_values()):
                        winner = True
                        break

                if winner:
                    print()
                    print(win_message)
                    sleep(5)
                    break

    def start(self):
        self.greet()
        self.random_board()
        self.print_fields()
        self.loop()


g = Game(ships={3: 1, 2: 2, 1: 4})
g.start()

