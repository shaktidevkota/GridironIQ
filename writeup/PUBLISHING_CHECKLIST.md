# Kaggle Publishing Checklist

Publishing is intentionally manual. Do not place Kaggle credentials in this repository or upload anything until you have reviewed the rendered notebook and write-up.

## 1. Register for the correct competition

1. Sign in to Kaggle and open the [NFL Big Data Bowl 2027 competition](https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/overview).
2. Review the current rules and click **Join Hackathon** / accept the rules if required. Confirm that your account is eligible to enter.
3. This project is an analytical Combine-to-NFL write-up, not a predictive CSV submission. The verified competition page has a **Writeups** area and requires a public Kaggle Notebook attached to a complete write-up. Use this competition's Writeups entry as the submission surface; do not invent a prediction-file schema.
4. The overview evaluates Football (30%), Data Science (30%), Write-up (20%), and Data Visualization (20%). The rules/page reviewed did not expose a separate named prediction track selector. If Kaggle presents a track/category selector during entry, confirm its current wording on the competition page and select the Big Data Bowl research/analysis or write-up category, not a prediction leaderboard category.

## 2. Publish and verify the notebook

1. Open the competition **Code** tab and choose **New Notebook** (or import `notebooks/gridiron_iq.ipynb`).
2. Add the official NFL Big Data Bowl 2027 dataset as notebook input. Keep the input attached to the notebook; the notebook discovers it beneath `/kaggle/input`.
3. Run all cells from a clean session. Confirm the size/schema checks pass, the selected cohort is `DL / SKILL_DRILLS_DL / PASS_RUSH_DRILL`, the sample and results are reproduced, and both figures render.
4. Confirm that `combine_to_rookie_tracking.png`, `cohort_coverage.png`, and the result CSVs are generated. Save a notebook version and set visibility to **Public**. Copy its public URL for the write-up.

## 3. Create and submit the competition Writeup

1. Open the competition **Writeups** tab and choose **Create New Writeup**.
2. Copy the contents of `writeup/final_submission.md` into the editor. Its local image paths are for repository preview and will not automatically resolve in Kaggle.
3. Upload and embed these local figures from `reports/figures/` at the corresponding image positions:
   - `combine_to_rookie_tracking.png`
   - `cohort_coverage.png`
4. Attach/link the **public** Kaggle Notebook URL from step 2. Confirm the embedded notebook and figures are visible to a signed-out/public viewer if the editor allows preview.
5. Select the NFL Big Data Bowl 2027 competition/write-up entry. If a separate track/category is presented, use the current competition's research/analysis write-up option as described in step 1; do not submit a fabricated prediction CSV.
6. Preview the complete entry, verify all metrics and image links, then explicitly click Kaggle's **Submit**, **Publish**, or equivalent final action. Saving a draft is not submission.
7. Verify Kaggle displays the write-up as published/submitted and retain the entry URL. The deadline reported by the authenticated CLI was **2027-01-06 23:59:00**; timezone was not specified, so verify the live competition page before relying on it.

## Final review

- [ ] Competition rules accepted; correct account/team and Big Data Bowl 2027 entry selected.
- [ ] Notebook is public, runs successfully with official attached data, and is linked from the write-up.
- [ ] Both PNG figures are uploaded and display in the write-up.
- [ ] Combine sensor tracking is explicitly linked to subsequent regular-season performance.
- [ ] Metrics, sample sizes, uncertainty, and limitations match the executed notebook.
- [ ] Final write-up was explicitly submitted/published and its status/URL verified.
