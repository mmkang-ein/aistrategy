"""
Multi-Agent Research Automation System
Usage:
  python main.py --mode academic --topic "transformer attention mechanism"
  python main.py --mode strategy --topic "AI 반도체 규제 동향 2025"
"""

import argparse
import asyncio
import sys
from pathlib import Path
from core.pipeline import ResearchPipeline
from core.logger import get_logger

logger = get_logger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Multi-Agent Research Automation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --mode academic --topic "ViT vs CNN image classification"
  python main.py --mode strategy --topic "생성형 AI 규제 동향 분석"
  python main.py --mode academic --topic "federated learning" --max-papers 20
        """
    )
    parser.add_argument("--mode", choices=["academic", "strategy"], required=True,
                        help="academic: 논문 연구 / strategy: AI 전략 리포트")
    parser.add_argument("--topic", required=True, help="연구 주제")
    parser.add_argument("--max-papers", type=int, default=10,
                        help="수집할 논문/자료 최대 수 (기본: 10)")
    parser.add_argument("--max-revisions", type=int, default=2,
                        help="리뷰 후 최대 revision 횟수 (기본: 2)")
    parser.add_argument("--output-dir", default=None,
                        help="출력 디렉토리 (기본: outputs/papers 또는 outputs/reports)")
    parser.add_argument("--verbose", action="store_true", help="상세 로그 출력")
    return parser.parse_args()


async def main():
    args = parse_args()

    print(f"\n{'='*60}")
    print(f"  Multi-Agent Research System")
    print(f"  모드: {'학술 논문 연구' if args.mode == 'academic' else 'AI 전략 리포트'}")
    print(f"  주제: {args.topic}")
    print(f"{'='*60}\n")

    pipeline = ResearchPipeline(
        mode=args.mode,
        topic=args.topic,
        max_papers=args.max_papers,
        max_revisions=args.max_revisions,
        output_dir=args.output_dir,
        verbose=args.verbose,
    )

    try:
        result = await pipeline.run()
        print(f"\n✅ 완료! 결과 파일: {result['output_path']}")
    except KeyboardInterrupt:
        print("\n⚠️  사용자가 중단했습니다.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Pipeline 오류: {e}", exc_info=True)
        print(f"\n❌ 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
