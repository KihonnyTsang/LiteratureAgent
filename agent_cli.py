from app.agent.runtime import (
    run_agent,
)


EXIT_COMMANDS = {
    "q",
    "quit",
    "exit",
}


def print_header() -> None:
    """
    打印 CLI 启动信息。
    """

    print(
        "=" * 80
    )

    print(
        "LiteratureAgent"
    )

    print(
        "本地科研文献智能分析系统"
    )

    print(
        "=" * 80
    )

    print(
        "输入科研问题开始分析。"
    )

    print(
        "输入 q / quit / exit 退出。"
    )


def print_answer(
    markdown: str,
) -> None:
    """
    输出 Agent Runtime 已经生成完成的 Markdown。

    CLI 只负责：

    1. 接收用户输入
    2. 调用统一 Agent Runtime
    3. 输出最终结果

    所有规划、工具调用和结果分流均由 Runtime 完成。
    """

    print()

    print(
        "=" * 80
    )

    print(
        "回答"
    )

    print(
        "=" * 80
    )

    print(
        markdown
    )


def main() -> None:
    """
    LiteratureAgent CLI 主入口。
    """

    print_header()

    while True:

        print()

        try:

            question = input(
                "请输入问题："
            ).strip()

        except (
            EOFError,
            KeyboardInterrupt,
        ):

            print()
            print(
                "已退出 LiteratureAgent。"
            )

            break

        # ====================================================
        # Exit
        # ====================================================

        if (
            question.lower()
            in EXIT_COMMANDS
        ):

            print(
                "已退出 LiteratureAgent。"
            )

            break

        # ====================================================
        # Empty input
        # ====================================================

        if not question:

            continue

        # ====================================================
        # Agent Runtime
        # ====================================================

        try:

            result = run_agent(
                question
            )

            print_answer(
                result.markdown
            )

        except Exception as error:

            print()

            print(
                "=" * 80
            )

            print(
                "执行失败"
            )

            print(
                "=" * 80
            )

            print(
                str(error)
            )


if __name__ == "__main__":
    main()