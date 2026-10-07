import asyncio, os
from pathlib import Path
from dotenv import load_dotenv
from meme_radar.collectors.factory import build_collectors
from meme_radar.pipeline import run_pipeline
from meme_radar.reporting.markdown import render
from meme_radar.reporting.json_report import render_json
from meme_radar.delivery.discord import deliver_discord

async def main():
    load_dotenv()
    collectors=build_collectors()
    if not collectors:
        raise RuntimeError("No collectors configured. Add X_BEARER_TOKEN or APIFY_TOKEN, or set USE_DEMO_DATA=true.")
    now,posts,candidates=await run_pipeline(collectors)
    report=render(candidates,now)
    report_json=render_json(candidates,now)
    outdir=Path(os.getenv("REPORT_DIR","./reports")); outdir.mkdir(parents=True,exist_ok=True)
    stem=f"meme-radar-{now.strftime('%Y%m%d-%H%M')}"
    md=outdir/f"{stem}.md"; js=outdir/f"{stem}.json"
    md.write_text(report,encoding="utf-8"); js.write_text(report_json,encoding="utf-8")
    (outdir/"latest.md").write_text(report,encoding="utf-8")
    try:
        delivery=await deliver_discord(candidates,now)
        if delivery["digest_sent"] or delivery["alerts_sent"]:
            print(f"Discord: digest={delivery['digest_sent']}, breakout_alerts={delivery['alerts_sent']}")
    except Exception as exc:
        raise RuntimeError(f"Discord delivery failed ({type(exc).__name__}); report saved locally.") from None
    print(report)
    print(f"\nCollected {len(posts)} posts. Saved: {md}")

if __name__=="__main__":
    asyncio.run(main())
