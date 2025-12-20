import os.path
import time

import project_crawler
import tkinter as tk
import tkinter.ttk as ttk
from enum import Enum, auto
from dataclasses import dataclass
import threading

class HighlighterMode(Enum):
    KEYWORD = "keyword"
    TYPE    = "type"
    MACRO   = "macro"
    STRING  = "string"
    NUMBER  = "number"
    COMMENT = "comment"

class CommentMode(Enum):
    NONE        = auto()
    AWAIT_NEXT  = auto()
    SINGLE_LINE = auto()
    MULTI_LINE  = auto()
    AWAIT_FINAL = auto()

@dataclass
class Config:
    id: HighlighterMode
    colour: str

@dataclass
class Word:
    word: str
    start: int
    end: int

KEYWORDS = (
    "alignas",
    "alignof",
    "auto",
    "bool",
    "break",
    "case",
    "char",
    "const",
    "constexpr",
    "continue",
    "default",
    "do",
    "double",
    "else",
    "enum",
    "extern",
    "false",
    "float",
    "for",
    "goto",
    "if",
    "inline",
    "int",
    "long",
    "nullptr",
    "register",
    "restrict",
    "return",
    "short",
    "signed",
    "sizeof",
    "static",
    "static_assert",
    "struct",
    "switch",
    "thread_local",
    "true",
    "typedef",
    "typeof",
    "typeof_unqual",
    "union",
    "unsigned",
    "void",
    "volatile",
    "while"
)

TYPES = (
    "bool",
    "char",
    "flag",
    "short",
    "int",
    "float",
    "long",
    "double",
    "unsigned",
    "vec3",
    "vec4",
    "mat3",
    "mat4"
)

class Colour:
    BACKGROUND = "#FAF9DE"
    FOREGROUND = "#000000"
    KEYWORD = "#92005E"
    TYPE = "#348596"
    STRING = "#0106C7"
    NUMBER = "#851DC5"
    COMMENT = "#567F62"
    MACRO = "#990000"

@dataclass
class Tag:
    id: HighlighterMode
    start: str
    end: str

class Highlighter:
    @staticmethod
    def split_str(text, delimiters):
        text += "\0"
        start_index = -1
        word_builder = ""
        word_list = list()
        for i, char in enumerate(text):
            if char in delimiters:
                if word_builder == "":
                    continue
                word_list.append(Word(word_builder, start_index, i))
                word_builder = ""
            else:
                if word_builder == "":
                    start_index = i
                word_builder += char

        return word_list

    @staticmethod
    def split_text(text):
        return Highlighter.split_str(text, delimiters=(" ", "\n", "\r", ";", ",", "(", ")", "{", "}", "\0"))

    @staticmethod
    def split_line(text):
        return Highlighter.split_str(text, delimiters=("\n", "\r",))

    @staticmethod
    def create_tag(tag_id, start, end) -> Tag:
        return Tag(
            tag_id, f"1.0+{start}c", f"1.0+{end}c"
        )

    def __init__(self):
        self.rules = dict()

    def add_rule(self, rule: HighlighterMode, colour: str):
        self.rules[rule] = colour

    def __generate_keyword(self, word_list: list[Word]) -> list[Tag]:
        tags = list()
        for word in word_list:
            if word.word in KEYWORDS:
                tags.append(self.create_tag(
                    HighlighterMode.KEYWORD, word.start, word.end
                ))
        return tags

    def __generate_type(self, word_list: list[Word]) -> list[Tag]:
        tags = list()
        for word in word_list:
            if word.word.strip("*") in TYPES:
                tags.append(self.create_tag(
                    HighlighterMode.TYPE, word.start, word.end
                ))
        return tags

    def __generate_macro(self, line_list: list[Word]) -> list[Tag]:
        tags = list()
        for line in line_list:
            if line.word.startswith("#"):
                tags.append(self.create_tag(
                    HighlighterMode.MACRO, line.start, line.end
                ))
        return tags

    def __generate_comment(self, text: str) -> list[Tag]:
        tags = list()
        start_index = -1
        comment_mode = CommentMode.NONE
        for i, char in enumerate(text):
            if comment_mode == CommentMode.NONE:
                if char == "/":
                    comment_mode = CommentMode.AWAIT_NEXT
            elif comment_mode == CommentMode.AWAIT_NEXT:
                if char == "/":
                    comment_mode = CommentMode.SINGLE_LINE
                    start_index = i
                elif char == "*":
                    comment_mode = CommentMode.MULTI_LINE
                    start_index = i
                else:
                    comment_mode = CommentMode.NONE
            elif comment_mode == CommentMode.SINGLE_LINE:
                if char in ("\n", "\r"):
                    comment_mode = CommentMode.NONE
                    tags.append(self.create_tag(
                        HighlighterMode.COMMENT, start_index - 1, i
                    ))
            elif comment_mode == CommentMode.MULTI_LINE:
                if char == "*":
                    comment_mode = CommentMode.AWAIT_FINAL
            elif comment_mode == CommentMode.AWAIT_FINAL:
                if char == "/":
                    comment_mode = CommentMode.NONE
                    tags.append(self.create_tag(
                        HighlighterMode.COMMENT, start_index - 1, i + 1
                    ))
                else:
                    comment_mode = CommentMode.MULTI_LINE
        return tags

    def __generate_string(self, text: str) -> list[Tag]:
        tags = list()
        start_index = -1
        in_string = False
        for i, char in enumerate(text):
            if char == "\"" and not in_string:
                in_string = True
                start_index = i
            elif char == "\"" and in_string:
                in_string = False
                tags.append(self.create_tag(
                    HighlighterMode.STRING, start_index, i + 1
                ))
        return tags

    def __generate_number(self, word_list: list[Word]) -> list[Tag]:
        tags = list()
        for word in word_list:
            try:
                if word.word.endswith("f"):
                    check_word = word.word[:-1]
                else:
                    check_word = word.word
                float(check_word)
                tags.append(self.create_tag(
                    HighlighterMode.NUMBER, word.start, word.end
                ))
            except ValueError:
                pass
        return tags

    def generate_tags(self, text) -> list[Tag]:
        tags = list()
        word_list = self.split_text(text)
        line_list = self.split_line(text)
        for rule, colour in self.rules.items():
            if rule == HighlighterMode.KEYWORD:
                tags.extend(self.__generate_keyword(word_list))
            elif rule == HighlighterMode.TYPE:
                tags.extend(self.__generate_type(word_list))
            elif rule == HighlighterMode.NUMBER:
                tags.extend(self.__generate_number(word_list))
            elif rule == HighlighterMode.STRING:
                tags.extend(self.__generate_string(text))
            elif rule == HighlighterMode.MACRO:
                tags.extend(self.__generate_macro(line_list))
            elif rule == HighlighterMode.COMMENT:
                tags.extend(self.__generate_comment(text))
        return tags

    def generate_configs(self) -> list[Config]:
        configs = list()
        for rule, colour in self.rules.items():
            configs.append(Config(
                rule, colour
            ))
        return configs

class EditorPanel(ttk.Frame):
    HEIGHT = 20

    def __init__(self, root, title="Default Title", editable=False, highlighter=None):
        super().__init__(root)
        self.title = ttk.Label(self, text=title)
        self.text = tk.Text(self, foreground=Colour.FOREGROUND, background=Colour.BACKGROUND)
        self.scroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.text.yview)
        self.text.config(yscrollcommand=self.scroll.set)
        self.editable = editable
        if not editable:
            self.text.config(state=tk.DISABLED)
        self.title.pack(side=tk.TOP)
        self.scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.pack(expand=True, fill=tk.BOTH)
        self.highlighter = highlighter
        if editable and highlighter is not None:
            self.master.after(10000, self.__recolour_loop)

        def tab_pressed(event: tk.Event) -> str:
            self.text.insert(tk.INSERT, "    ")
            return "break"

        self.text.bind("<Tab>", tab_pressed)

    def __guard(self, func, *args, **kwargs):
        if not self.editable:
            self.text.config(state=tk.NORMAL)
        func(*args, **kwargs)
        if not self.editable:
            self.text.config(state=tk.DISABLED)

    def __write(self, text):
        self.text.delete("1.0", tk.END)
        self.text.insert(tk.INSERT, text)
        self.__highlight()

    def write(self, text):
        self.__guard(self.__write, text)

    def __str__(self):
        return self.text.get("1.0", "end-1c")

    def __highlight(self):
        for config in self.highlighter.generate_configs():
            self.text.tag_configure(config.id.value, foreground=config.colour)

        for tag in self.highlighter.generate_tags(str(self)):
            self.text.tag_add(tag.id.value, tag.start, tag.end)

    def highlight(self):
        if self.highlighter is None:
            return
        self.__guard(self.__highlight)

    def __recolour_loop(self):
        self.highlight()
        self.master.after(10000, self.__recolour_loop)

    def clear(self):
        self.__guard(self.text.delete, "1.0", tk.END)

    def __insert_at_start(self, text):
        self.text.insert("1.0", text)
        self.__highlight()

    def insert_at_start(self, text):
        self.__guard(self.__insert_at_start, text)

@dataclass
class CheckerResult:
    doxygen: bool
    comment_ratio: float

class Checker:
    def __init__(self, file_name, file_data):
        self.__file_name = file_name
        self.__lines = file_data.split("\n")
        self.__report: project_crawler.Report | None = None

    @staticmethod
    def check_doxygen(report):
        if report.doxygen_comment is None:
            return False

        contain_dict = dict()
        param_lines = [i for i in report.doxygen_comment if "@param" in i]
        is_valid = True

        for param in report.params:
            for i, line in enumerate(param_lines):
                if param.name in line:
                    contain_dict[param.name] = i
            if param.name not in contain_dict.keys():
                contain_dict[param.name] = -1
                is_valid = False

        if report.returns == "exception":
            contains_throws = False
            for line in report.doxygen_comment:
                if "@throws" in line and len(line) > len(" * @throws "):
                    contains_throws = True
                    break
            if not contains_throws:
                is_valid = False
        elif report.returns != "void":
            contains_returns = False
            for line in report.doxygen_comment:
                if "@return" in line and len(line) > len(" * @return "):
                    contains_returns = True
                    break
            if not contains_returns:
                is_valid = False

        return is_valid

    @staticmethod
    def check_comment_ratio(report):
        return report.num_comments / report.num_lines > 0.1

    def check(self):
        for i in range(len(self.__lines)):
            report = project_crawler.generate_function_report(self.__file_name, self.__lines, i)
            if report is not None:
                self.__report = report
                return CheckerResult(
                    doxygen=self.check_doxygen(report),
                    comment_ratio=report.num_comments / report.num_lines
                )
        return None

    def generate_doxygen(self):
        if self.__report is None:
            self.check()

        if self.__report is None:
            return None

        doxygen = "/**\n * \n"
        for param in self.__report.params:
            doxygen += f" * @param {param.name} \n"
        if self.__report.returns == "exception":
            doxygen += " * @throws \n"
        elif self.__report.returns != "void":
            doxygen += " * @return \n"
        doxygen += " */\n"
        return doxygen

class Window(tk.Tk):
    TITLE = "Comment Buggerer"

    def __init__(self):
        super().__init__()
        self.title(Window.TITLE)
        self.geometry("1280x720")
        self.running = False
        self.protocol("WM_DELETE_WINDOW", self.stop)
        self.loader = threading.Thread(target=self.loader_target)
        self.loaded = threading.Event()
        self.already_loaded = False
        self.load_time = 0
        self.file_queue: list[project_crawler.Report] = list()
        self.active_file = ""
        self.active_func = None
        self.active_checker = None
        self.num_functions = 0

        highlighter = Highlighter()
        highlighter.add_rule(HighlighterMode.KEYWORD, Colour.KEYWORD)
        highlighter.add_rule(HighlighterMode.TYPE, Colour.TYPE)
        highlighter.add_rule(HighlighterMode.NUMBER, Colour.NUMBER)
        highlighter.add_rule(HighlighterMode.STRING, Colour.STRING)
        highlighter.add_rule(HighlighterMode.MACRO, Colour.MACRO)
        highlighter.add_rule(HighlighterMode.COMMENT, Colour.COMMENT)

        # main editor section
        self.editor = ttk.Frame(self)

        self.original = EditorPanel(self.editor, title="Original Code", highlighter=highlighter)
        self.final = EditorPanel(self.editor, title="Final Version", editable=True, highlighter=highlighter)

        self.original.grid(row=0, column=0, sticky="NSEW")
        self.final.grid(row=0, column=1, sticky="NSEW")

        self.editor.columnconfigure(0, weight=1)
        self.editor.columnconfigure(1, weight=1)
        self.editor.rowconfigure(0, weight=1)

        # side panel
        self.controller = ttk.Frame(self)

        self.centre_buttons = ttk.Frame(self.controller)

        self.clear_button = ttk.Button(self.centre_buttons, text="Clear", command=self.final.clear)
        self.clear_button.pack(padx=6, pady=3)
        self.copy_button = ttk.Button(self.centre_buttons, text="Copy", command=self.copy_original)
        self.copy_button.pack(padx=6, pady=3)
        self.gen_doxygen = ttk.Button(self.centre_buttons, text="Insert\nDoxygen", command=self.insert_doxygen)
        self.gen_doxygen.pack(padx=6, pady=3)

        self.accept_button = ttk.Button(self.controller, text="Accept", command=self.push)
        self.accept_button.pack(padx=6, pady=3, side=tk.BOTTOM)

        self.centre_buttons.pack(side=tk.RIGHT)

        # bottom panel
        self.base = ttk.Frame(self)

        self.load_label = ttk.Label(self.base, text="Loading file tree...")
        self.completion = ttk.Label(self.base)
        self.update_completion()
        self.splitter_a = ttk.Separator(self.base, orient=tk.VERTICAL)
        self.ratio = ttk.Label(self.base)
        self.update_comment_ratio(0)
        self.splitter_b = ttk.Separator(self.base, orient=tk.VERTICAL)
        self.doxygen = ttk.Label(self.base)
        self.update_doxygen(False)

        self.load_label.pack(side=tk.LEFT)
        self.completion.pack(side=tk.RIGHT)
        self.splitter_a.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        self.ratio.pack(side=tk.RIGHT)
        self.splitter_b.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        self.doxygen.pack(side=tk.RIGHT)

        self.base.pack(fill=tk.X, side=tk.BOTTOM)
        self.controller.pack(side=tk.RIGHT, fill=tk.Y)
        self.editor.pack(expand=True, fill=tk.BOTH, side=tk.LEFT)

    def update_completion(self):
        if self.num_functions != 0:
            num_left = len(self.file_queue)
            ratio = (self.num_functions - num_left) / self.num_functions
        else:
            num_left = 0
            ratio = 0.0
        self.completion.config(text=f"{ratio*100:.3f}% Complete ({num_left} of {self.num_functions} remaining)")

    def update_comment_ratio(self, ratio):
        colour = "red" if ratio < 0.1 else "green"
        self.ratio.config(text=f"Comment: {ratio*100:.0f}%", foreground=colour)

    def update_doxygen(self, doxy_valid):
        colour = "green" if doxy_valid else "red"
        self.doxygen.config(text=f"Doxygen: {"OK" if doxy_valid else "Invalid"}", foreground=colour)

    def loader_target(self):
        curr_time = time.perf_counter_ns()
        file_tree = project_crawler.generate_file_tree(project_root=os.path.expanduser("~/CLionProjects/TekPhysics/"))

        def process_file(f_path):
            f_data = project_crawler.read_file(f_path)
            f_lines = f_data.split("\n")
            for i in range(len(f_lines)):
                report = project_crawler.generate_function_report(f_path, f_lines, i)
                if report is None:
                    continue

                if not (Checker.check_comment_ratio(report) and Checker.check_doxygen(report)):
                    self.file_queue.append(report)

                self.num_functions += 1

        file_queue = list()
        file_queue.append(file_tree)
        while len(file_queue) > 0:
            file_tree = file_queue.pop(-1)
            for file_name, file_data in file_tree.items():
                if type(file_data) == dict:
                    file_queue.append(file_data)
                else:
                    process_file(file_data)

        self.load_time = (time.perf_counter_ns() - curr_time) / 1000000
        self.loaded.set()

    def copy_original(self):
        original_text = str(self.original)
        self.final.write(original_text)

    def advance_editor(self):
        self.active_func = self.file_queue.pop()
        self.active_file = self.active_func.file
        with open(self.active_file) as f_ptr:
            file_data = f_ptr.read()
        file_lines = file_data.split("\n")
        func_data = "\n".join(file_lines[self.active_func.start_line:self.active_func.start_line+self.active_func.num_lines])
        self.original.write(func_data)
        self.final.clear()
        self.title(f"{Window.TITLE} | editing '{self.active_func.name}()' of '{os.path.basename(self.active_file)}'")
        self.update_completion()
        self.active_checker = Checker(self.active_file, str(self.final))

    def overwrite_func(self):
        with open(self.active_file, "r") as f_ptr:
            file_data = f_ptr.read()

        file_lines = file_data.split("\n")
        new_lines = str(self.final).split("\n")
        final_lines = list()
        final_lines.extend(file_lines[:self.active_func.start_line])
        final_lines.extend(new_lines)
        final_lines.extend(file_lines[self.active_func.start_line+self.active_func.num_lines:])

        with open(self.active_file, "w") as f_ptr:
            f_ptr.write("\n".join(final_lines))

    def insert_doxygen(self):
        if self.active_checker is None:
            return
        doxygen = self.active_checker.generate_doxygen()
        if doxygen is None:
            return
        self.final.insert_at_start(doxygen)

    def push(self):
        self.overwrite_func()
        self.advance_editor()

    def stop(self):
        self.running = False

    def run(self):
        self.loader.start()
        self.running = True
        prev_time = time.perf_counter_ns()
        while self.running:
            if not self.already_loaded and self.loaded.is_set():
                self.already_loaded = True
                self.load_label.configure(text=f"Loaded file tree in {self.load_time:.1f}ms")
                self.advance_editor()

            curr_time = time.perf_counter_ns()
            if curr_time >= prev_time + int(1e9):
                prev_time = curr_time
                checker = Checker(self.active_file, str(self.final))
                result = checker.check()
                if result is not None:
                    self.update_doxygen(result.doxygen)
                    self.update_comment_ratio(result.comment_ratio)
                else:
                    self.update_doxygen(False)
                    self.update_comment_ratio(0.0)
                self.active_checker = checker

            self.update()
            self.update_idletasks()

def main():
    window = Window()
    window.run()

if __name__ == "__main__":
    main()
