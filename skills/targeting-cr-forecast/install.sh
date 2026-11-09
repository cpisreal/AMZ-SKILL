#!/usr/bin/env bash
# 把 targeting-cr-forecast 安装到 DSH 的某个 skill 根目录
# 用法: ./install.sh [project|user]
set -euo pipefail

SKILL_NAME="targeting-cr-forecast"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "${1:-project}" in
  project)
    DEST="$(pwd)/.dsh/skills"
    ;;
  user)
    # DSH Beta 用 ~/.dsh-beta；Stable 版请改成 ~/.dsh
    DEST="${DSH_SKILLS_DIR:-$HOME/.dsh-beta/skills}"
    ;;
  *)
    echo "用法: $0 [project|user]" >&2
    exit 2
    ;;
esac

TARGET="$DEST/$SKILL_NAME"

echo "源  : $SRC"
echo "目标: $TARGET"

mkdir -p "$DEST"

# 只允许删除名字精确匹配的这一个 skill 目录
if [ -e "$TARGET" ]; then
  case "$TARGET" in
    */skills/"$SKILL_NAME") rm -rf -- "$TARGET" ;;
    *) echo "拒绝删除非预期路径: $TARGET" >&2; exit 1 ;;
  esac
fi

cp -R "$SRC" "$TARGET"
rm -rf -- "$TARGET/__pycache__" "$TARGET/scripts/__pycache__"

echo "已安装: $TARGET"
echo "自检  : python \"$TARGET/scripts/forecast_cr.py\" --check-env"
echo
echo "提示: DSH 会监视 skill 根目录, 无需重启, 下一次会话目录即可见。"
