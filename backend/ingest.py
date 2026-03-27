import argparse
import json

from rag import DEFAULT_TOPIC_QUERIES, build_rag_index


def main():
    parser = argparse.ArgumentParser(description="Build or refresh the Her Circle medical RAG index.")
    parser.add_argument(
        "--query",
        action="append",
        dest="queries",
        help="Add a topic query to index. You can pass this more than once.",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Keep the existing index and upsert into it instead of resetting first.",
    )
    parser.add_argument(
        "--live-discovery",
        action="store_true",
        help="Also try live source discovery during ingestion. Slower and more likely to hit site blocking.",
    )
    args = parser.parse_args()

    queries = args.queries or DEFAULT_TOPIC_QUERIES
    manifest = build_rag_index(
        queries=queries,
        reset=not args.keep,
        include_live_discovery=args.live_discovery,
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
