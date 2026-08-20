#!/bin/bash
# Read all sheets and save CSV data to individual files
# Note: Sheet list may change — re-run "wecom-cli sheet get" to verify current sheets

DOCID="e3_Ab0AvAZQADUCNsqxNFQf1QUy2puYy"
OUTDIR="sheet_data"
mkdir -p "$OUTDIR"

declare -A SHEETS
SHEETS[hb5wxe]="米开老师-Ivory"
SHEETS[BB08J2]="张颜清-Anakin"
SHEETS[g8lkcs]="才鼎龙-Parker"
SHEETS[t6yzbv]="刘适妤-Naomi"
SHEETS[p0q6uh]="方露-Luna"
SHEETS[h9uq1n]="上官旭东-Alex"
SHEETS[q1blqg]="黄心如Shannon"
SHEETS[zj12m5]="艾尔夏提Earry"

for sid in hb5wxe BB08J2 g8lkcs t6yzbv p0q6uh h9uq1n q1blqg zj12m5; do
  name="${SHEETS[$sid]}"
  echo "Reading $name ($sid)..."
  wecom-cli sheet ranges get --json "{\"docid\":\"$DOCID\",\"sheet_id\":\"$sid\",\"mode\":\"csv\"}" > "$OUTDIR/${sid}.json" 2>&1
  echo "  -> saved to ${sid}.json"
done

echo "Done. All sheets saved to $OUTDIR"
