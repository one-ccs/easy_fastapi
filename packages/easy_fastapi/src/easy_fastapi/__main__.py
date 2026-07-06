"""python -m easy_fastapi 入口。

委托给 _runner.main 做 argv 分发。仅为内部执行通道，不对外宣传；
对用户主入口始终是 efa（由 CLI 包持有）。
"""

from easy_fastapi._runner import main

if __name__ == "__main__":
    main()
