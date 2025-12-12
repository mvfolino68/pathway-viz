#!/usr/bin/env python3
"""
PathwayViz CLI

Usage:
    python -m pathway_viz                       # Run the Pathway+Kafka demo
    python -m pathway_viz --mode simple         # Run a no-Docker demo
    python -m pathway_viz --port 8080           # Run on custom port

    pathway-viz init my-project                 # Scaffold a new project
    pathway-viz init my-project --k8s           # Include Kubernetes manifests
    pathway-viz show docker-compose             # Print template to stdout
    pathway-viz templates                       # List available templates
"""

import argparse
import sys


def cmd_demo(args):
    """Run the demo."""
    if args.mode == "simple":
        import pathway_viz as sv

        sv.run_demo(port=args.port)
        return

    from pathway_viz.demos import run_demo

    run_demo(port=args.port)


def cmd_init(args):
    """Initialize a new project."""
    from pathway_viz._cli import init_project

    try:
        init_project(
            target_dir=args.directory,
            include_k8s=args.k8s,
            force=args.force,
        )
    except FileExistsError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_show(args):
    """Show a template."""
    from pathway_viz._cli import show_template

    try:
        show_template(args.template)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_templates(args):
    """List available templates."""
    from pathway_viz._cli import list_templates

    list_templates()


def main():
    parser = argparse.ArgumentParser(
        prog="pathway-viz",
        description="PathwayViz - Real-time dashboards for streaming data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Demo command (also the default)
    demo_parser = subparsers.add_parser("demo", help="Run the demo")
    demo_parser.add_argument(
        "--port", "-p", type=int, default=3000, help="Server port (default: 3000)"
    )
    demo_parser.add_argument(
        "--mode",
        choices=["pathway", "simple"],
        default="pathway",
        help="'pathway' (requires Kafka) or 'simple' (no Docker)",
    )
    demo_parser.set_defaults(func=cmd_demo)

    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize a new project")
    init_parser.add_argument("directory", help="Directory to create the project in")
    init_parser.add_argument("--k8s", action="store_true", help="Include Kubernetes manifests")
    init_parser.add_argument("--force", "-f", action="store_true", help="Overwrite existing files")
    init_parser.set_defaults(func=cmd_init)

    # Show command
    show_parser = subparsers.add_parser("show", help="Print a template to stdout")
    show_parser.add_argument("template", help="Template name (e.g., docker-compose, Dockerfile)")
    show_parser.set_defaults(func=cmd_show)

    # Templates command
    templates_parser = subparsers.add_parser("templates", help="List available templates")
    templates_parser.set_defaults(func=cmd_templates)

    args = parser.parse_args()

    # If no subcommand, run demo with legacy argument handling
    if args.command is None:
        # Check for legacy --mode and --port args
        legacy_parser = argparse.ArgumentParser()
        legacy_parser.add_argument("--port", "-p", type=int, default=3000)
        legacy_parser.add_argument("--mode", choices=["pathway", "simple"], default="pathway")
        legacy_args = legacy_parser.parse_args()
        legacy_args.func = cmd_demo
        cmd_demo(legacy_args)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
