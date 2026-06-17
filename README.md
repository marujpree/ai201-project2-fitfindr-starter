# FitFindr

FitFindr is an AI agent that helps users find thrifted clothing and style it. You give it a query like "vintage graphic tee under $30" and it searches a mock thrift dataset, picks the best match, suggests how to wear it with your existing wardrobe, and generates a social media caption for the outfit.

<!--
This starter kit contains everything you need to begin Project 2.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```
-->

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project root and add your Groq API key (free at [console.groq.com](https://console.groq.com)):

```
GROQ_API_KEY=your_key_here
```

Then run the app:

```bash
python app.py
```

Open the URL shown in your terminal (usually `http://localhost:7860`).

<!--
## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.
-->

---

## Tool Inventory

### `search_listings(description, size, max_price)`

**Purpose:** Searches the mock thrifted listings dataset and returns the listings that best match what the user is looking for.

**Inputs:**
- `description` (str): plain English description of what the user wants, like "vintage graphic tee". Used for keyword scoring against listing titles and descriptions.
- `size` (str or None): size to filter by, like "M" or "XL". Matching is case insensitive and substring based so "M" will match "S/M". Pass `None` to skip size filtering.
- `max_price` (float or None): the maximum price the user is willing to pay, inclusive. Pass `None` to skip price filtering.

**Output:** A list of listing dicts sorted by relevance score, best match first. Each dict has `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`. Returns an empty list if nothing matches.
---

### `suggest_outfit(new_item, wardrobe)`

**Purpose:** Takes the selected thrift item and the user's wardrobe and asks the LLM to put together one or two outfit ideas. Gives general styling advice if the wardrobe is empty.

**Inputs:**
- `new_item` (dict): the top listing returned by `search_listings`. The prompt uses `title`, `category`, `style_tags`, `colors`, and `condition`.
- `wardrobe` (dict): a dict with an `"items"` key containing a list of wardrobe item dicts. Each item has `name`, `category`, `colors`, and `style_tags`. The list can be empty and the tool handles that case.

**Output:** A non empty string with outfit suggestions. If the wardrobe has items it references them by name. If the wardrobe is empty it gives general advice about what pairs well with the item's style and colors.

---

### `create_fit_card(outfit, new_item)`

**Purpose:** Writes a short social media caption for the thrift find. Meant to sound like a real person posted it, not a product description. Runs at high temperature so each call produces something a little different.

**Inputs:**
- `outfit` (str): the suggestion string from `suggest_outfit`. If this is empty or whitespace only, the function returns an error string without calling the LLM at all.
- `new_item` (dict): the listing dict. The prompt uses `title`, `price`, `platform`, `style_tags`, and `condition`.

**Output:** A 2 to 4 sentence caption that mentions the item name, price, and platform naturally. Uses temperature 0.95 so the wording varies across calls. If `outfit` is empty it returns `"Cannot generate fit card: no outfit suggestion provided."` instead of calling the LLM.

---

## Planning Loop

The planning loop lives in `run_agent()` inside `agent.py`. Here is how it decides what to do:

1. **Parse the query.** The raw user query goes to the Groq LLM with a prompt that asks it to extract `description`, `size`, and `max_price` as JSON. Temperature is set to 0.0 here so the extraction is deterministic. The result gets stored in `session["parsed"]`.

2. **Search for listings.** `search_listings` runs with the parsed values. Results go into `session["search_results"]`.

3. **Branch on results.** This is the key decision point. If results is empty the loop sets `session["error"]` to a specific message that tells the user what failed and gives concrete suggestions like removing the size filter, raising the budget, or trying different keywords. Then it returns early without calling the other two tools.

4. **Select the top item.** If results exist `results[0]` (the highest scoring match) gets stored in `session["selected_item"]`.

5. **Suggest an outfit.** `suggest_outfit` runs with the selected item and the wardrobe. Output goes into `session["outfit_suggestion"]`.

6. **Generate the fit card.** `create_fit_card` runs with the outfit suggestion and selected item. Output goes into `session["fit_card"]`.

7. **Return the session.** The Gradio interface reads the session dict and maps it to the three output panels.

The agent never calls `suggest_outfit` or `create_fit_card` when search comes back empty. Those tools only run when there is actually something to work with.

---

## State Management

All state lives in a single session dict initialized by `_new_session()` at the start of each run. Nothing is global, no values are hardcoded between steps.

Here is how data flows between tools:

- `session["query"]` is the original user input. It is only used by the LLM query parser.
- `session["parsed"]` comes from the parser and feeds directly into `search_listings` as its three arguments.
- `session["search_results"]` is set by `search_listings` and checked immediately by the planning loop to decide whether to continue or exit early.
- `session["selected_item"]` is `results[0]` from the search. The exact same dict object is passed into both `suggest_outfit` and `create_fit_card`.
- `session["wardrobe"]` is set by the caller at the start and passed directly into `suggest_outfit`.
- `session["outfit_suggestion"]` comes from `suggest_outfit` and is passed straight into `create_fit_card`.
- `session["fit_card"]` is the final output.
- `session["error"]` is `None` on a successful run and gets set to a message string on early exit.

The Gradio handler in `app.py` checks `session["error"]` first. If it is set it shows the error in the first panel and leaves the other two empty. If it is not set it formats the selected item and maps the other fields to their panels.

---

## Error Handling

| Tool | Failure mode | What the agent does |
|------|-------------|---------------------|
| `search_listings` | No listings match the query | Sets `session["error"]` to a message like "No listings found for 'designer ballgown' under $5 in size XXS. Try removing the size filter, raising your budget above $5, using different keywords." Returns without calling the other tools. |
| `suggest_outfit` | Wardrobe is empty | Sends a different prompt to the LLM asking for general styling advice instead of wardrobe specific outfits. Returns that string and continues to `create_fit_card`. |
| `create_fit_card` | `outfit` string is empty | Returns `"Cannot generate fit card: no outfit suggestion provided."` without making an LLM call. Stored in `session["fit_card"]`, agent returns normally. |
| `suggest_outfit` / `create_fit_card` | LLM call throws an exception | `suggest_outfit` returns `"Outfit suggestion unavailable. Try pairing this with your current wardrobe."` and `create_fit_card` returns `"Fit card generation failed. Please try again."` |

**Concrete example from testing:**

Running the impossible query `"designer ballgown size XXS under $5"` directly through `search_listings` returns `[]` with no exception. Running it through `run_agent` produces:

```
No listings found for 'designer ballgown' under $5 in size XXS. Try removing the size filter, raising your budget above $5, using different keywords.
```

The session has `fit_card = None` and `outfit_suggestion = None` because those tools were never called.

---

## AI Tool Usage

**Instance 1: Implementing `search_listings`**

I gave Claude the Tool 1 spec from my `planning.md` which included the inputs with types, the return format, and the failure mode. I also described the scoring approach I wanted: keyword overlap between the user's description and the listing's title plus description combined. Claude produced a working implementation that used `load_listings()` correctly and sorted by score. The main thing I changed was making the scoring loop simpler since Claude originally split the scoring into a separate function that felt like extra abstraction I did not need. I also checked that it returned an empty list and not `None` when nothing matched before trusting it.

**Instance 2: Implementing `run_agent` and the query parser**

I gave Claude the Planning Loop and State Management sections of my `planning.md` plus the session dict structure already in `agent.py`. I asked it to implement `run_agent()` and also to add a `_parse_query()` helper that uses the LLM to extract structured JSON from the user's free text query. Claude added the helper using `temperature=0.0` which I kept since deterministic parsing makes sense here. I checked that the branch logic actually returned early when results were empty and that it was not just calling all three tools unconditionally regardless of what came back from search.

---

## Spec Reflection

The part that went most smoothly was the planning loop branching logic. Because I had written out the exact conditions in `planning.md` before touching any code, the implementation basically just followed the steps in order. Having the state management table written out in advance also helped since I could check each assignment in the code against what I had described.

The trickiest part was the query parser. I originally thought about just scanning the user's text for a number to use as the price and a letter like "M" or "L" for the size, but that would have broken on anything phrased differently than expected. Using the LLM at temperature 0.0 to pull out structured JSON was way more reliable and handled things like "under thirty dollars" or "fits a medium" without needing any extra code for every possible variation.

One thing I would do differently is write the pytest tests before implementing the tools instead of after. I had the failure mode tests written in `planning.md` which helped but I wrote the actual `test_tools.py` file after the implementation was already done. Writing them first would have caught a couple things faster.
