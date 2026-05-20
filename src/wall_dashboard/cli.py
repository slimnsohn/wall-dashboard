"""CLI for manual probing during dev and one-time setup steps."""
from __future__ import annotations

import asyncio
import io
import sys
import zipfile
from pathlib import Path

import httpx
import typer
from rich.console import Console
from rich.table import Table

from . import amtrak, aqi, metra, weather
from .amtrak import parse_csv
from .config import get_settings
from .stations import AmbiguousStation, resolve_station

app = typer.Typer(help="Wall Dashboard CLI")
console = Console()


@app.command()
def bootstrap_nws() -> None:
    """Resolve NWS hourly forecast URL. Prints the line to paste into .env."""
    url = asyncio.run(weather.bootstrap_nws_url())
    console.print(f"[bold]NWS_FORECAST_HOURLY_URL[/bold]={url}")
    console.print("Paste that line into your .env on the Green.")


@app.command()
def stations(search: str) -> None:
    """Look up Metra stop_ids by name or stop_id."""
    r = httpx.get("https://schedules.metrarail.com/gtfs/schedule.zip", timeout=60)
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    stops = parse_csv(z.read("stops.txt").decode("utf-8"))
    try:
        s = resolve_station(stops, search)
        console.print(f"[bold]{s['stop_id']}[/bold]\t{s['stop_name']}")
    except AmbiguousStation as exc:
        table = Table(title=f"Multiple matches for {search!r} - be specific")
        table.add_column("stop_id")
        table.add_column("stop_name")
        for m in exc.matches:
            table.add_row(m["stop_id"], m["stop_name"])
        console.print(table)
        sys.exit(2)
    except KeyError:
        console.print(f"[red]No station matching {search!r}[/red]")
        sys.exit(1)


@app.command()
def probe() -> None:
    """Hit every data source once and print availability. Deploy smoke test."""
    async def run():
        s = get_settings()
        m = await metra.get_metra(s.northbrook_stop_id)
        w = await weather.get_weather()
        a = await aqi.get_aqi()
        data_dir = Path("data")
        am = amtrak.get_amtrak(data_dir)
        for name, r in [("metra", m), ("amtrak", am), ("weather", w), ("aqi", a)]:
            status = (
                "[green]OK[/green]"
                if r["available"] else f"[red]FAIL: {r['error']}[/red]"
            )
            console.print(f"{name:10s} {status}")
    asyncio.run(run())


@app.command(name="refresh-amtrak")
def refresh_amtrak() -> None:
    """Force an immediate Amtrak GTFS download + extract."""
    result = asyncio.run(amtrak.refresh_amtrak_schedule(Path("data")))
    console.print(result)


if __name__ == "__main__":
    app()
