import sys
import re

# 模块级常量
OPERATORS = {'+', '-', '*', '/'}
ALLOWED_CHARS = set('0123456789+-*/().% ')

def validate_expression(expression: str) -> str | None:
    """
    验证数学表达式是否合法。
    返回错误信息字符串（如果非法）或 None（如果合法）。
    """
    # 检查是否为空
    if not expression or not expression.strip():
        return "输入为空，请输入一个数学表达式"

    # 检查是否包含非法字符
    for char in expression:
        if char not in ALLOWED_CHARS:
            return f"非法字符 '{char}'，仅允许数字、运算符(+-*/)和括号"

    # 分词处理（保持数字和运算符的连续块）
    tokens = []
    current_token = ""
    for char in expression:
        if char in OPERATORS or char in '()':
            if current_token:
                tokens.append(current_token)
                current_token = ""
            tokens.append(char)
        else:
            current_token += char
    if current_token:
        tokens.append(current_token)

    # 检查运算符连续出现（如 "2++3"）
    prev_was_operator = False
    for token in tokens:
        is_operator = token in OPERATORS
        if is_operator and prev_was_operator:
            if token == '-':
                # 允许负号，如 "2+-3"
                continue
            return f"运算符连续出现：'...{token}...'"
        prev_was_operator = is_operator

    # 检查缺失运算符：数字或右括号后面直接跟数字或左括号
    for i in range(len(tokens) - 1):
        current = tokens[i]
        next_token = tokens[i + 1]
        current_is_num = current.replace('.', '', 1).lstrip('-').isdigit()
        next_is_num = next_token.replace('.', '', 1).lstrip('-').isdigit()
        current_is_rparen = current == ')'
        next_is_lparen = next_token == '('
        
        if (current_is_num or current_is_rparen) and (next_is_num or next_is_lparen):
            return "数字/括号之间缺少运算符"

    # 检查括号匹配
    balance = 0
    for char in expression:
        if char == '(':
            balance += 1
        elif char == ')':
            balance -= 1
        if balance < 0:
            return "括号不匹配：多余的右括号"
    if balance != 0:
        return "括号不匹配：缺少右括号"

    # 检查除以零（在计算时会更准确，这里做初步检查）
    if '/0' in expression.replace(' ', ''):
        return "除数为零"

    return None


def safe_eval(expression: str) -> str:
    """
    安全计算数学表达式，返回结果字符串或错误信息。
    """
    # 验证表达式
    error = validate_expression(expression)
    if error:
        return f"错误: {error}"

    try:
        # 使用 Python 的 eval 进行计算，但限制可用功能
        # 只允许基本的数学运算，通过限制命名空间提高安全性
        result = eval(expression, {"__builtins__": {}}, {
            "abs": abs, "round": round, "int": int, "float": float
        })
        return f"结果: {result}"
    except ZeroDivisionError:
        return "错误: 除数为零"
    except SyntaxError:
        return "错误: 表达式语法错误"
    except Exception as e:
        return f"错误: 计算时发生异常: {str(e)}"


def main():
    """
    命令行计算器主函数
    """
    print("=" * 40)
    print("  命令行计算器 v1.0")
    print("  支持的运算: +, -, *, /")
    print("  支持括号和浮点数")
    print("  输入 'exit' 或 'quit' 退出")
    print("=" * 40)

    while True:
        try:
            user_input = input("\n请输入表达式: ").strip()
            
            # 检查退出命令
            if user_input.lower() in ('exit', 'quit', 'q'):
                print("感谢使用，再见！")
                break
            
            # 计算并输出结果
            if user_input:
                result = safe_eval(user_input)
                print(result)
            else:
                print("错误: 输入为空，请输入一个数学表达式")
                
        except KeyboardInterrupt:
            print("\n\n检测到中断，退出程序。")
            break
        except EOFError:
            print("\n\n输入结束，退出程序。")
            break


if __name__ == "__main__":
    main()