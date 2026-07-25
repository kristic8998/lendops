# LendOps Studio — User Guide

Written for a non-programmer. Everything in the app is click-driven, and every page repeats these instructions in its own on-screen "How to use" card. Your data never leaves your computer.

## First launch (60 seconds)

Open LendOps from the Start menu. You land on **Home**, which links to the three modules. Each module has a **"Try with sample data"** button — click it first to see a full run with realistic demo data before using your own files. The ◐ button (or **Ctrl+D**) switches dark/light mode; **Ctrl+1…4** jump between pages.

## Your files

Plain **CSV or Excel** exports from your loan system work as-is. There is no template: columns are recognised by name (e.g. `dpd`, `Current DPD Days`, `overdue_days` all work). If a column is missing, the app simply works with what it has. Three ready-made example files ship in the `sample_data` folder.

## ☎ Collecta — who do we call today?

1. **① Upload Active Loans** — pick your active loan book. Useful columns (all optional): loan id, name, phone, segment, monthly income, loan amount, outstanding, EMI, current DPD, missed payments.
2. **② Analyze Risk** — every loan gets a 0–100 score, a **High/Medium/Low** band (red/orange rows), and a plain-English *top risk driver* ("already past due", "EMI is heavy vs income"…). Loans 60+ days past due are always High. If your file includes an outcome column (e.g. `defaulted` from a past cycle), the scoring automatically upgrades to a model trained on your own book — the label under the cards tells you which was used.
3. **③ Export Calling List** — saves an Excel workbook: *Calling List* (worst first, phones included; untick "Include medium risk" for High only), *All Loans Scored*, and *Summary*.

## ⚖ PolicySim — what if our rules were stricter?

1. **Upload Historical Loans** — a closed book that includes how each loan ended (a `defaulted` yes/no column is required; the app tells you if it's missing).
2. **Tick the rules to test** and drag the sliders: cap loan amount, minimum income, loan-to-income cap, exclude students, reprice APR. Unticked rules are off.
3. **▶ Run Simulation** — the headline shows the net-profit impact; the table compares the actual book vs the rule-filtered one (loans, disbursed, interest, losses, net profit, default rate), the grid lists every declined loan with the first rule it failed, and the assumptions are printed below the table. **Export Report** saves it all to Excel.

## 🛡 KYC Sentinel — is today's batch clean?

1. **① Upload Daily Applications** — today's application file. Useful columns: name, DOB, age, PAN/ID, bank account, phone, email, income, requested amount.
2. **② Scan for Fraud** — **red rows are alerts** (same bank account or ID under different names, underage applicants, stated age contradicting DOB); **orange rows need review** (shared phones/emails, invalid PAN format, missing critical fields, requested amount over 20× income). The `flags` column says exactly why, and "Show flagged rows only" hides the clean ones.
3. **③ Export Report** — saves *Flagged*, *All Applications*, and a per-check *Summary* sheet for the risk team.

## Where results are saved

Exports default to `%LOCALAPPDATA%\LendOps\reports`, but the save dialog lets you choose anywhere. More help: [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
