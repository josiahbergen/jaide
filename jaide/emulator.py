# jaide.py
# jaide emulator
# josiah bergen, january 2026


from .util.logger import logger


class Emulator:
    def __init__(self):
        self.memory = bytearray(0xFFFF + 1) # 64k
        self.registers = {"A": 0, "B": 0, "C": 0, "D": 0, "X": 0, "Y": 0, "SP": 0, "PC": 0, "Z": 0, "F": 0, "MB": 0, "STS": 0}
        self.breakpoints = []
        self.halted = False

    def load_binary(self, file: str):
        with open(file, "rb") as f:
            binary = f.read()
        self.memory[:len(binary)] = binary

    def run(self):
        self.step()

    def step(self):
        logger.warning("not implemented", "emulator.py:step()")

    def repl(self):

        print("starting repl version 0.0.1...")
        print("welcome to the emulator! type 'help' for a list of commands.")

        def assert_num_args(num: int):
            if len(args) != num:
                print(f"invalid number of arguments for command {command}. (expected {num}, got {len(args)})")
                return False
            return True
        
        while True:

            command, *args = input("jaide > ").split()

            match command:

                case "step":
                    self.step()

                case "run":
                    self.run()

                case "load":
                    if not assert_num_args(1):
                        continue
                    self.load_binary(args[0])

                case "help":
                    print("help: show this message")
                    print("step: execute one instruction")
                    print("run: execute until halted")
                    print("quit: exit the emulator")

                case "quit":
                    self.halted = True
                    break

                case _:
                    print("invalid command. type 'help' for a list of commands.")


    