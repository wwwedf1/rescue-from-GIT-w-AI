#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试GUI语言切换功能
"""

import tkinter as tk
from src.gui import RefactoredGitRescuerGUI
import time

def test_language_switch():
    """测试语言切换功能"""
    root = tk.Tk()
    app = RefactoredGitRescuerGUI(root)
    
    print("GUI已启动，请测试语言切换按钮...")
    print("点击🌐按钮应该能切换所有UI文本的语言")
    
    # 运行GUI
    root.mainloop()

if __name__ == "__main__":
    test_language_switch() 