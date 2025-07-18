#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git对象拯救工具 - GUI启动脚本
"""

import tkinter as tk
from src.gui import RefactoredGitRescuerGUI

def main():
    """启动GUI界面"""
    root = tk.Tk()
    app = RefactoredGitRescuerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 