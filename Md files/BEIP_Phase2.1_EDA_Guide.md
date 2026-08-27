# BEIP — Phase 2.1: Exploratory Data Analysis (EDA)
### Task Guide

This phase has one goal: **understand your data before you try to predict anything.**

Before you can train an ML model, you need to know:
- What does the data actually look like?
- Are there patterns you can see with your eyes before an algorithm does?
- Which columns have too many missing values to be useful?
- Are there obvious things that affect who wins an election?

EDA is the detective work that tells you what features to use in Phase 2.2.

---

## What Is a Jupyter Notebook?

A Jupyter Notebook (`.ipynb` file) is a document that mixes **text, code, and charts** in one place.
You write Python code in "cells" and run them one at a time. The output (charts, tables, numbers)
appears directly below the cell.

This is the standard tool for data exploration in data science. You are **not** writing
production scripts here — you are asking questions and drawing pictures of your data.

---

## Existing Files You Will Use

These files **already exist** in your project. You will be reading from them / using them as data sources.

### 1. `src/config.py`
**What it is:** The database connection helper.
**Why you need it:** Every notebook connects to your PostgreSQL database to load data.
You will import `get_engine()` from this file at the top of every notebook.

```python
# You will use this line at the top of every notebook
import sys
sys.path.insert(0, "..")      # tells Python to look in the project root for src/
from src.config import get_engine
```

---

### 2. `silver.election_results` (Database Table)
**What it is:** Cleaned Lok Sabha election results — one row per candidate per election.
**Why you need it:** This is your primary dataset. Every analysis starts here.
**Key columns you'll use:**
| Column | What it means |
|---|---|
| `year` | Election year (2009, 2014, 2019...) |
| `state_name` | State the constituency belongs to |
| `constituency_name` | Name of the voting area |
| `candidate_name` | The candidate's name |
| `party` | Standardized party name (BJP, INC, AAP...) |
| `votes` | Number of votes the candidate received |
| `vote_share` | % of total votes the candidate got |
| `position` | Finishing position — **1 = Winner** |
| `electors` | Total registered voters in the constituency |
| `turnout_percentage` | % of registered voters who actually voted |

---

### 3. `silver.candidate_affidavits` (Database Table)
**What it is:** Candidate affidavit data from MyNeta — what they declared about themselves.
**Why you need it:** This tells you about the candidate as a person (wealth, criminal history, education).
**Key columns you'll use:**
| Column | What it means |
|---|---|
| `criminal_cases` | Number of criminal cases declared |
| `serious_criminal_cases` | Number of serious cases (murder, rape, robbery etc.) |
| `has_criminal_case` | Boolean: True if any criminal case |
| `total_assets` | Total declared wealth in INR |
| `is_crorepati` | Boolean: True if assets > ₹1 Crore |
| `education` | Bucketed education level (Graduate, Post Graduate, etc.) |

---

### 4. `silver.census_demographics` (Database Table)
**What it is:** Census 2011 district-level demographics — one row per district.
**Why you need it:** It gives you the context of where the election happened (how literate, how populated).
**Key columns you'll use:**
| Column | What it means |
|---|---|
| `state_name` | State name (matches election data) |
| `district_name` | Name of the district |
| `total_population` | Total people in the district |
| `literacy_rate` | % of population that is literate |
| `sex_ratio` | Females per 1000 males |
| `sc_percentage` | % Scheduled Caste population |
| `st_percentage` | % Scheduled Tribe population |

---

### 5. `gold.candidate_features` (Database Table)
**What it is:** The flat, joined table produced by `src/ml/feature_engineering.py`.
**Why you need it:** This is the combined view of all three Silver tables — one row per candidate
with everything joined together. Useful for correlation analysis.

> **Note:** This table only exists if you have run `python -m src.ml.feature_engineering` first.

---

## New Files to Create

### Directory: `notebooks/`
**Create this new folder** at the root of the project:
```
c:\Projects\BEIP\notebooks\
```
**Why:** Notebooks are exploratory tools, not production code. Keeping them in a separate
`notebooks/` folder away from `src/` keeps the project clean and signals to anyone reading
the codebase that these are for analysis only.

---

### New File 1: `notebooks/01_eda_election_results.ipynb`
**What it is:** A Jupyter Notebook exploring the core election results data.
**Why:** This is your most important dataset. Understanding it first tells you what
the target variable (`won`) looks like and what raw patterns exist before you model them.

**Tasks to complete inside this notebook:**

#### Setup Cell (always first)
```python
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import sys
sys.path.insert(0, "..")
from src.config import get_engine

engine = get_engine()
df = pd.read_sql("SELECT * FROM silver.election_results", engine)
print(df.shape)
```

#### Task A — Basic Overview
- [ ] Run `df.head()` — look at the first 5 rows. Do they make sense?
- [ ] Run `df.dtypes` — are the data types what you expect? (year should be int, vote_share should be float)
- [ ] Run `df.isnull().sum()` — which columns have missing data? How bad is it?
- [ ] Run `df.describe()` — what are the min/max/mean values for votes, vote_share, position?
- [ ] **Write a comment** above each output explaining what you notice.

#### Task B — Election Year Distribution
- [ ] Count how many candidates ran in each year: `df.groupby('year').size()`
- [ ] Plot a bar chart of candidates per year
- [ ] **Question to answer:** Which years have the most data? Are any years missing?

#### Task C — Party Analysis
- [ ] Count total candidates per party (top 20)
- [ ] Count total **wins** per party: filter where `position == 1`
- [ ] Calculate **win rate** per party: `wins / total_candidates`
- [ ] Plot a horizontal bar chart of win rate for top 15 parties
- [ ] **Question to answer:** Which party has the highest win rate? Does it surprise you?

#### Task D — Vote Share Distribution
- [ ] Plot a histogram of `vote_share` for all candidates
- [ ] Plot two histograms overlaid: winners (`position == 1`) vs losers (`position != 1`)
- [ ] Find the **median vote share needed to win** per year
- [ ] **Question to answer:** What vote share does a candidate typically need to win?
  Is there a threshold below which no one wins?

#### Task E — Turnout by State
- [ ] Calculate average `turnout_percentage` per state
- [ ] Plot a horizontal bar chart, sorted from highest to lowest
- [ ] **Question to answer:** Which states consistently have high/low turnout?
  Is there a pattern (North vs South, rural vs urban)?

#### Task F — Add the Target Variable
- [ ] Create a new column: `df['won'] = (df['position'] == 1).astype(int)`
- [ ] Print: `df['won'].value_counts()` — how many winners vs losers overall?
- [ ] Calculate the **class imbalance ratio**: how many losers per winner?
- [ ] **Why this matters:** If 90% of your data is "lost", a model that always predicts
  "lost" gets 90% accuracy but is useless. You need to know this number before training.

---

### New File 2: `notebooks/02_eda_candidate_affidavits.ipynb`
**What it is:** A Jupyter Notebook exploring candidate wealth and criminal history.
**Why:** Candidate affidavit data is some of the most analytically rich data in Indian
elections. The ADR (Association for Democratic Reforms) has done extensive research showing
candidates with criminal cases and higher assets win more often. You want to verify this
in your own data before trusting it as an ML feature.

**Tasks to complete inside this notebook:**

#### Setup Cell
```python
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import sys
sys.path.insert(0, "..")
from src.config import get_engine

engine = get_engine()

# Load affidavits joined with election results (so we know who won)
df = pd.read_sql("""
    SELECT a.*, e.position, e.vote_share,
           CASE WHEN e.position = 1 THEN 1 ELSE 0 END as won
    FROM silver.candidate_affidavits a
    LEFT JOIN silver.election_results e
        ON a.year = e.year
        AND a.state_name = e.state_name
        AND a.constituency_name = e.constituency_name
        AND a.candidate_name = e.candidate_name
""", engine)
```

#### Task A — Data Coverage
- [ ] How many candidates have affidavit data vs total candidates in election_results?
- [ ] Which years have good affidavit coverage? Which don't?
- [ ] **Why this matters:** If 2009 data has only 20% affidavit coverage, you should
  restrict your ML model to 2014/2019 only.

#### Task B — Criminal Cases
- [ ] What % of candidates declared at least 1 criminal case?
- [ ] Plot a bar chart: % of candidates with criminal cases by party (top 15 parties)
- [ ] Compare win rates: `has_criminal_case = True` vs `False`
  ```python
  df.groupby('has_criminal_case')['won'].mean()
  ```
- [ ] **Question to answer:** Do candidates with criminal cases win **more** or **less** often?
  (The answer from national data: they win MORE — this is a known phenomenon in Indian politics)

#### Task C — Wealth / Assets
- [ ] Plot a histogram of `total_assets` — you'll see it's extremely skewed (a few billionaires)
- [ ] Plot the same histogram but with **log scale on x-axis** — this will look much more useful
- [ ] What % of candidates are crorepatis (`total_assets > 1 Crore`)?
- [ ] Compare win rates: `is_crorepati = True` vs `False`
- [ ] **Question to answer:** Do wealthier candidates win more often?

#### Task D — Education
- [ ] Plot a bar chart of the `education` column — what's the most common education level?
- [ ] Calculate win rate by education level:
  ```python
  df.groupby('education')['won'].mean().sort_values(ascending=False)
  ```
- [ ] **Question to answer:** Does higher education correlate with winning?

#### Task E — Correlation Matrix
- [ ] Select numeric columns: `criminal_cases`, `total_assets`, `vote_share`, `won`
- [ ] Plot a heatmap: `sns.heatmap(df[cols].corr(), annot=True)`
- [ ] **Question to answer:** Which features correlate most strongly with `won`?

---

### New File 3: `notebooks/03_eda_census.ipynb`
**What it is:** A Jupyter Notebook exploring district-level demographic data.
**Why:** Census data adds geographic context to your model. Knowing the literacy rate or
SC/ST population percentage of a constituency helps the model understand structural factors
beyond the individual candidate.

**Tasks to complete inside this notebook:**

#### Setup Cell
```python
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import sys
sys.path.insert(0, "..")
from src.config import get_engine

engine = get_engine()
census = pd.read_sql("SELECT * FROM silver.census_demographics", engine)
```

#### Task A — Basic Overview
- [ ] How many districts are covered?
- [ ] How many states?
- [ ] Run `census.isnull().sum()` — any missing values?

#### Task B — Literacy Rate by State
- [ ] Calculate average literacy rate per state
- [ ] Plot a horizontal bar chart, sorted highest to lowest
- [ ] **Question to answer:** Which states have the highest/lowest literacy?
  Does it match what you know about India?

#### Task C — Sex Ratio by State
- [ ] Plot sex ratio (females per 1000 males) by state
- [ ] **Question to answer:** Which states have a low sex ratio?

#### Task D — Population Distribution
- [ ] Plot a histogram of `total_population` per district
- [ ] **Question to answer:** What's the range? Are most districts small with a few
  massive ones (like urban districts)?

#### Task E — Join with Election Data (Cross-Dataset Analysis)
```python
# Load state-level averages from election results
elections = pd.read_sql("""
    SELECT state_name, AVG(turnout_percentage) as avg_turnout
    FROM silver.election_results
    GROUP BY state_name
""", engine)

# Aggregate census to state level
state_census = census.groupby('state_name')['literacy_rate'].mean().reset_index()

# Join
combined = state_census.merge(elections, on='state_name', how='inner')
```
- [ ] Scatter plot: `literacy_rate` (x-axis) vs `avg_turnout` (y-axis) per state
- [ ] Add state name labels to the points
- [ ] **Question to answer:** Is there a correlation between literacy and turnout?
  More literate states — do they vote more or less?

---

## File Summary

```
c:\Projects\BEIP\
│
├── notebooks\                                      ← CREATE THIS FOLDER
│   ├── 01_eda_election_results.ipynb               ← CREATE — Core election analysis
│   ├── 02_eda_candidate_affidavits.ipynb           ← CREATE — Wealth & criminal cases
│   └── 03_eda_census.ipynb                         ← CREATE — District demographics
│
├── src\
│   └── config.py                                   ← USE (don't modify) — DB connection
│
└── requirements.txt                                ← MODIFY — add packages below
```

### Packages to add to `requirements.txt`
```
jupyter
notebook
matplotlib
seaborn
ipykernel
```

---

## How to Start Jupyter

```bash
# From the project root (c:\Projects\BEIP)
jupyter notebook
```

This opens a browser at `http://localhost:8888`.
Navigate to `notebooks/` → click **New** → select **Python 3** to create a new notebook.
Save with the exact filenames listed above.

---

## Key Questions EDA Should Answer

By the end of all three notebooks, you should know:

| # | Question | Data Source |
|---|---|---|
| 1 | What vote share does a candidate need to win? | `election_results` |
| 2 | Which party has the highest win rate? | `election_results` |
| 3 | Which states have the highest voter turnout? | `election_results` |
| 4 | What % of candidates have criminal cases? | `candidate_affidavits` |
| 5 | Do candidates with criminal cases win more often? | both |
| 6 | Do wealthier candidates win more often? | both |
| 7 | Which education level has the best win rate? | both |
| 8 | Does district literacy correlate with turnout? | `census` + `election_results` |

**These 8 answers directly determine which features you will use in Phase 2.2 model training.**

---

## Done? Move to Phase 2.2

Once all three notebooks are complete and you can answer the 8 questions above,
you are ready for:

> **Phase 2.2 — Feature Engineering & Model Training**
> Next files: `src/ml/train.py`, `src/ml/evaluate.py`
