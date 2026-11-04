#!/usr/bin/env python3
"""
convert_rule_provider.py

把仓库根目录下所有 Clash / mihomo 格式的 rule-provider YAML（payload 列表）
转换为 Shadowrocket RULE-SET 用的 .list 文件（每行一条、不带策略）。

在仓库根目录或 scripts/ 目录下运行均可：
    python3 scripts/convert_rule_provider.py

无第三方依赖，仅使用 Python 标准库。
"""

import re
import sys
from pathlib import Path

# 脚本位于 scripts/ 下，规则文件在仓库根目录
ROOT = Path(__file__).resolve().parent.parent

# IP 类规则需追加 no-resolve，避免命中时触发 DNS 解析
IP_TYPES = {"IP-CIDR", "IP-CIDR6", "GEOIP", "IP-ASN"}

# Shadowrocket .list 暂不支持的规则类型
UNSUPPORTED = {"RULE-SET", "SUB-RULE", "AND", "OR", "NOT"}


def strip_comment(line: str) -> str:
    """去掉行尾注释（' # 备注' 形式，# 前有空格）。"""
    return re.sub(r"\s+#.*$", "", line).strip()


def parse_payload(text: str) -> list:
    """从 rule-provider YAML 中提取 payload 规则列表（不依赖 PyYAML）。"""
    rules = []
    in_payload = False
    for raw in text.splitlines():
        stripped = raw.strip()
        if re.match(r"^payload\s*:", stripped):
            in_payload = True
            continue
        if in_payload:
            if stripped.startswith("- "):
                rule = strip_comment(stripped[2:])
                if rule:
                    rules.append(rule)
            elif stripped and not stripped.startswith("#"):
                break  # 离开 payload 小节
    return rules


def convert(rule: str):
    """把一条 Clash 规则转成 .list 行（不带策略）。"""
    parts = [p.strip() for p in rule.split(",")]
    if len(parts) < 2:
        return None
    rtype = parts[0].upper()
    if rtype in UNSUPPORTED:
        print(f"  [跳过] 不支持的规则类型: {rule}")
        return None
    if rtype in IP_TYPES:
        return "{},{}".format(parts[0], parts[1]) + ",no-resolve"
    return "{},{}".format(parts[0], parts[1])


def main():
    yaml_files = sorted(ROOT.glob("*.yaml"))
    if not yaml_files:
        print("仓库根目录没有找到 .yaml 文件")
        return 1

    for yaml_path in yaml_files:
        out_path = yaml_path.with_suffix(".list")
        payload = parse_payload(yaml_path.read_text(encoding="utf-8"))
        if not payload:
            print(f"[跳过] {yaml_path.name}: 未找到 payload 规则")
            continue

        lines = [converted for converted in (convert(r) for r in payload) if converted]
        if not lines:
            print(f"[跳过] {yaml_path.name}: 没有可转换的规则")
            continue

        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[完成] {yaml_path.name} -> {out_path.name} ({len(lines)} 条规则)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
