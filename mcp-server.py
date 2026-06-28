## MCP server
from mcp.server.fastmcp import FastMCP
import httpx
import shutil
import subprocess


mcp = FastMCP("my-first-mcp-server", json_response=True)


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@mcp.tool()
def get_weather(city: str) -> str:
    """Get the LIVE, real-time current temperature in Celsius for any city.
    Always use this tool when the user asks about current weather, today's
    temperature, or conditions in any city. Do not answer from memory."""
    # Open-Meteo needs lat/lon, so we first geocode the city name.
    geo_data = httpx.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1},
        timeout=10,
    ).json()

    if not geo_data.get("results"):
        return f"Could not find city '{city}'."

    place = geo_data["results"][0]
    lat, lon = place["latitude"], place["longitude"]

    temp = httpx.get(
        "https://api.open-meteo.com/v1/forecast",
        params={"latitude": lat, "longitude": lon,
                "current_weather": True},
        timeout=10,
    ).json()["current_weather"]["temperature"]

    result = f"Current temperature in {place['name']}: {temp}°C"
    return result


@mcp.tool()
def get_exchange_rate(base: str, target: str) -> str:
    """Get the latest exchange rate from `base` currency to `target` currency.

    Use 3-letter ISO codes, e.g. base='USD' target='INR'.
    """
    data = httpx.get(
        "https://api.frankfurter.dev/v1/latest",
        params={"from": base.upper(), "to": target.upper()},
        timeout=10,
    ).json()

    if "rates" not in data:
        return f"Could not fetch rate for {base} → {target}."
    rate = data["rates"][target.upper()]
    result = f"1 {base.upper()} = {rate} {target.upper()} (as of {data['date']})"
    return result


@mcp.tool()
def get_mac_system_info() -> str:
    """Return current disk space and memory usage on this Mac."""

    # --- Disk ---
    disk = shutil.disk_usage("/")
    total_disk = disk.total / (1024 ** 3)
    used_disk = disk.used / (1024 ** 3)
    free_disk = disk.free / (1024 ** 3)

    # --- Memory (macOS-specific sysctls) ---
    mem_bytes = int(
        subprocess.run(["sysctl", "-n", "hw.memsize"],
                       capture_output=True, text=True).stdout.strip()
    )
    total_mem = mem_bytes / (1024 ** 3)

    # vm_stat reports page counts; the header tells us the page size.
    vm_output = subprocess.run(
        ["vm_stat"], capture_output=True, text=True).stdout
    # 16 KB is default on Apple Silicon and it is  updated from header if different
    page_size = 16384
    for line in vm_output.splitlines():
        if "page size of" in line:
            page_size = int(line.split("page size of")[
                            1].split("bytes")[0].strip())
            break

    pages_free = pages_inactive = 0
    for line in vm_output.splitlines():
        if line.startswith("Pages free:"):
            pages_free = int(line.split(":")[1].strip().rstrip("."))
        elif line.startswith("Pages inactive:"):
            pages_inactive = int(line.split(":")[1].strip().rstrip("."))

    free_mem = (pages_free + pages_inactive) * page_size / (1024 ** 3)
    used_mem = total_mem - free_mem

    result = (
        f"=== Disk (/) ===\n"
        f"  Total : {total_disk:.1f} GB\n"
        f"  Used  : {used_disk:.1f} GB  ({used_disk / total_disk * 100:.1f}%)\n"
        f"  Free  : {free_disk:.1f} GB\n\n"
        f"=== Memory ===\n"
        f"  Total : {total_mem:.1f} GB\n"
        f"  Used  : {used_mem:.1f} GB  ({used_mem / total_mem * 100:.1f}%)\n"
        f"  Free  : {free_mem:.1f} GB  (pages free + inactive)"
    )

    return result


if __name__ == "__main__":
    mcp.run(transport="stdio")
