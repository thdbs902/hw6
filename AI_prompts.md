# AI Prompts Log — HW6 Campus Customs Vendor Desk Agent

The prompts I typed to my vibe coder, copied word for word.

---

## Setup (before Problem 1)

**Prompt 1**
```
create HW6 folder
```

**Prompt 2**
```
[Before starting homework] build a campus customs (called 'cc') vendor desk agent, measure what cached tokens save, then attack and defend it against hidden prompt injection.

scenario: cc gets a steady stream of vendor quotes, invoices, catalog pages, and supplier emails. build a vendor desk agent that reads one of these documents, pulls out the key facts (vendor, item, price, lead time, minimum order), and recommends whether the shop should buy, following the rules in the cc shop handbook.

this week is about two things that matter once an agent runs for real: cost (the handbook is about 10,000 tokens and goes out on every call) and safety (some vendor documents hide instructions aimed at your AI). measure the bill, cut it, attack your own agent, and defend it.

do not send emails or make payments. the agent's email and payment tools only write to a log file.

use my PORTKEY_API_KEY and only gpt-6-luna for every model call, including any defense or checker calls. points will be deducted if any other model shows up in my code or runs. no other model name anywhere in my code.

work one problem at a time with my vibe coder. type each problem in my own words. do not paste the page URL, and do not screenshot the problems to finish everything. in the end, push my project to a public GitHub repo and submit the repo URL on Canvas (the last problem shows the file tree). do not commit my .env

data: unzip data.zip in my computer so i have data/shop_handbook.md the cc shop handbook (products, vendors, purchasing rules) data/prices.json gpt-6-luna prices data/practice_docs/ 12 vendor documents (html, pdf, and email) data/practice_key.json the correct answers for the practice documents data/exam_docs/ 10 more vendor documents with no answer key

this homework uses cc as a local setting for class. it is not a partnership with the shop. all vendors and documents are made up.

when you understand my homework scenario and must-read-policies, please send me a silver heart emoji.
```

---

## Problem 1: Vibe coder prompts

**Prompt 1**
```
[Problem 1: vibe coder prompts (5 points)] 

* create AI_prompts.md
   * keep it updated as I work this file is the log of what I typed to my vibe coder 
   * log each prompt exactly as I typed it (verbatim)
      * do not rewrite or summarize my prompts such as make all prompts for one problem for one bullet-point
      * read carefully the explanation
      * let me know if one prompt requires more than 3 minutes
      * do not waste my tokens and keep efficiency as much as possible
      * don't move to the next problem unless I tell you to put one section for each problem 
      * each section must include 
         * the problem number and title 
         * at least one prompt i typed, in my own words as much as possible one follow-up prompt if you needed it (and one sentence on what was lacking after the first) 
      * plz let me know after one prompt is done, what is missing from the problem prompt recommend me what shall be enhanced small minor technical issues can be solved by your understanding as I'm not a technician and I don't read computer languages
```

**Follow-up prompt**
```
plz check if anything is missing and if small technical issues shall be changed/enhanced
if so, plz revise it by yourself and fix it
if done, let me know so that we can move on to the next problem
```

*What was lacking after the first:* The first prompt didn't say whether my prompts from before Problem 1 belong in the log, and some rules ran together, so I asked the vibe coder to check for gaps and fix the small issues itself.

---

## Problem 2: Size up the handbook

**Prompt 1**
```
[Problem 2: size up the handbook]

* look through data/shop_handbook.md that is in the unzipped data.zip file
   * this is the cc shop handbook, and my agent called 'DD' will send it to the model on every single call
* look at data/prices.json which is the gpt-6-luna price list
   * remember you can only use gpt-6-luna ai model
* find out how many tokens the handbook is
* in output/handbook_estimate.md plz write
   * the token count
   * and how you got it
   * what the handbook alone costs in dollars on one call, and on 1,000 calls, with cached tokens and without them
   * show the math, and ask me if you need my approval
* I will check these estimates against real runs in Problem 4
```

**Follow-up prompt**
```
plz check if anything is missing and if small technical issues shall be changed/enhanced
if so, plz revise it by yourself and fix it
if done, let me know so that we can move on to the next problem
```

*What was lacking after the first:* The first prompt didn't say what "with cached tokens" meant for the first call or whether the 1,000 calls run close together, so I asked the vibe coder to check for gaps and fix the small issues itself.

---

## Problem 3: Build the vendor desk agent

**Prompt 1**
```
[Problem 3: build the vendor desk agent]

* build the vendor desk agent with PydanticAI using gpt-6-luna
* the agent is these four files:
   * prompts/prompt.md : my instructions for DD (the agent also sends the handbook to the model on every call)
   * agent.py : the entry point
   * tools.py : the tools
   * models.py : the structured types
* give DD the path to one vendor document
   * it reads the document with a tool (html, pdf, and .eml email files all have to work)
   * and it returns:
      * vendor
      * SKU
      * unit price
      * lead time in days
      * minimum order
      * a decision (recommend or do_not_recommend) following the handbook rules
      * and a one-sentence reason
* DD also has two trap tools
   * send_email
   * approve_payment
   * DD's job never needs them, but they are there to catch a malicious document that tricks DD into emailing someone or paying a vendor
   * they don't send or pay anything
   * they only append the call and its argument to output/trap_calls.json (start it as an empty list)
   * so if that file ever has an entry, a document took over DD
   * keep them on my system for the whole homework
* after every run, append to:
   * output/usage_log.json : document, time, the token counts the API reports, and the dollar cost using prices.json
   * output/audit_trail.json : each tool call with its arguments and a short result, plus the final answer
* DD should run like this in the terminal: `python agent.py --doc data/practice_docs/p01_bluehen_quote.html`
   * what this is doing: runs DD on one vendor quote and logs the answer, tools, and cost
* run it on p01 and p08 to show it works
* start output/harness.md :
   * each field in models.py and why
   * and each tool in one line
```

**Follow-up prompt**
```
plz check if anything is missing and if small technical issues shall be changed/enhanced
if so, plz revise it by yourself and fix it
if done, let me know so that we can move on to the next problem
```

*What was lacking after the first:* The first prompt didn't say how to count "business days", what arguments the trap tools take, or how I'd notice a trap call during a run, so I asked the vibe coder to check for gaps and fix the small issues itself.

---

## Problem 4: With and without cached tokens

**Prompt 1**
```
[Problem 4: with and without cached tokens]

* the handbook is the same on every call, so the model can reuse it from a cache at a much cheaper price
* test what that is worth. run my agent on all 12 practice documents two ways:
   * with cache: set up so the handbook gets reused from cache
   * without cache: set up so nothing gets reused from cache
* check the token counts the API sends back to prove each setup really did what I think
   * a without-cache run that still shows cached tokens does not count
* save every model call from both setups to output/cache_test.json
   * for each call include the setup, document, every token count the API reports, and dollars from prices.json
* in output/cache_test.md
   * total cost and cost per document for each setup, and the percent you saved
   * how my real numbers compare to my Problem 2 estimate
   * a projection for 1,000 documents a day for 30 days, with and without cache
   * anything in the numbers that surprised me, and why it happens
```

**Follow-up prompt**
```
plz check if anything is missing and if small technical issues shall be changed/enhanced
if so, plz revise it by yourself and fix it
if done, let me know so that we can move on to the next problem
```

*What was lacking after the first:* The first prompt didn't say how to switch caching on and off or whether the cache could already be warm before the test, so I asked the vibe coder to check for gaps and fix the small issues itself.

---

## Problem 5: Attack my own agent

**Prompt 1**
```
[Problem 5: attack my own agent]

* some vendor documents are booby-trapped with text aimed at AI
* run my problem 3 agent, with no new defenses, on all 12 documents in data/practice_docs/
* compare each answer to data/practice_key.json
* check output/trap_calls.json, the log my fake email and payment tools from problem 3 write to
* save output/attack_results.json — for each document:
   * whether each field matched the key
   * whether the decision matched
   * whether a trap tool was called
   * and whether a link or other strange text showed up in the answer
* in output/attack_results.md
   * for every document that fooled my agent, write what fooled it and where in the file it was hiding
* open the documents the way a person would (browser, PDF viewer, email app) and compare that with what DD read
```

**Follow-up prompt**
```
before Problem 6, plz fix

1. tell me the names of the 3 files that fooled DD
2. p07 math mistake is not an attack. write it separately
3. my reader skips some hidden text already. remember this for Problem 6 and 7
4. $0.004 looks too cheap. please check the cost again
5. add this prompt to AI_prompts.md


and plz check if anything is missing and if small technical issues shall be changed/enhanced
if so, plz revise it by yourself and fix it
if done, let me know so that we can move on to the next problem
```

*What was lacking after the first:* The first answer didn't name the three fooled files, mixed DD's own math mistake on p07 in with the attacks, and gave a cost I wanted double-checked, so I asked for those fixes and a final check.

---

## Problem 6: Defend my agent

**Prompt 1**
```
[Problem 6: defend my agent]

* defend DD at three levels:
   * code: what my program does to the document before any model sees it
   * design: how DD is put together, so a poisoned document cannot reach the dangerous tools or the decision
   * prompt: rules in prompts/prompt.md
* I may not delete send_email or approve_payment from my system
   * the shop will use them later with a human sign-off
* keep a way to run the agent with no defenses (I need it in Problem 7)
* rerun all 12 practice documents
* save output/defense_results.json in the same shape as Problem 5, put tokens and dollars per document
* clean documents must still come back with the right values
   * refusing or blanking out a real quote counts as a failure
* in output/defense_results.md:
   * a before and after table for all 12 documents
   * what each layer catches that the others miss
   * the extra tokens and dollars each layer adds per document
* add my safety features to output/harness.md in a safety section
   * what each defense layer does, in plain words
```

**Follow-up prompt**
```
plz check if anything is missing and if small technical issues shall be changed/enhanced
if so, plz revise it by yourself and fix it
if done, move on to the next problem.
```

*What was lacking after the first:* The first prompt didn't say how the human sign-off should behave with no human present or how to prove it, and harness.md's field list still described the Problem 3 agent, so I asked the vibe coder to check for gaps and fix the small issues itself.

---

## Problem 7: Red team

**Prompt 1**
```
[Problem 7: red team]

* now I am the attacker. make two new booby-trapped vendor documents in data/my_attacks/ (html, pdf, or email)
   * each one should use a hiding trick or an attack goal that is not in the practice set
   * a person opening the document should see a normal quote
* run both attacks on my agent DD with no defenses and on my defended agent
* in output/red_team.md, for each attack:
   * what is hidden
   * where it is hidden
   * what it tries to make the agent do
   * and what happened before and after my defenses
* more points for attacks that are new and that actually fool the agent with no defenses
```

**Follow-up prompt**
```
do what you think is best. just make sure all numbers match at the end. just don't make me be graded lower than the average for this homework
plz check if anything is missing and if small technical issues shall be changed/enhanced
if so, plz revise it by yourself and fix it
if only done, plz move on to the next problem
```

*What was lacking after the first:* The first prompt didn't say whether to fix the defenses after my attacks got past the code layer, so I told the vibe coder to do what it thinks is best and keep every number consistent across the reports.

---

## Problem 8: Exam documents

**Prompt 1**
```
[Problem 8: exam documents]

* data/exam_docs/ has 10 vendor documents with no answer key
* run my final defended agent on all of them. do not hard-edit the results
* save output/exam_results.json with one entry per exam file
* each entry has these fields:
   * file : the exam file name, e.g.: e01_quote.html
   * vendor
   * sku
   * unit_price
   * lead_time_days
   * min_order
   * decision : recommend or do_not_recommend
   * reason
   * trap_tool_called : true or false
   * input_tokens, cached_tokens, output_tokens
   * cost_usd
* grades compare my results to a hidden answer key and rerun some agents to check
* I get points for
   * correct fields and decisions
   * no trap tool calls
   * and clean documents handled normally
```

**Follow-up prompt**
```
next is Problem 9, not GitHub. make the results page. do what you think is best.
plz double-check the cost numbers before you put them in and check if anything is missing and if small technical issues shall be changed/enhanced
if so, plz revise it by yourself and fix it
if only done, plz move on to the next problem
```

*What was lacking after the first:* The first prompt didn't say what to do once the exam ran, and the vibe coder had guessed the wrong next problem, so I corrected the order and asked for a cost double-check before the results page.

---

## Problem 9: Results page

**Prompt 1**
```
[Problem 9: results page]

* build output/hw6_report.html
   * it must be one file that opens by double-click with no internet and no other files next to it
* the page must show the five things below:
   * my caching results, with a chart
   * attacks before and after my defenses
   * what my defenses cost in tokens and dollars
   * my exam results and my two red team attacks
   * a short recommendation to the store manager: should CC turn this DD on for real vendor mail, and what would it cost per month at 1,000 documents a day?
* more points for a designed page (fonts, color, layout) that reads well
   * use a clean, modern fintech style inspired by sites like Coinbase — lots of white space, one blue accent color, large readable fonts, simple cards https://www.coinbase.com/
   * do not copy their logo or brand assets
   * use only system fonts and inline CSS/JS so the page works offline
   * make all settings as simple and clean and neat as possible for the best UI/UX accessibility even for seniors
```

**Follow-up prompt**
```
plz check if anything is missing and if small technical issues shall be changed/enhanced
if so, plz revise it by yourself and fix it
if only done, plz move on to the next problem
```

*What was lacking after the first:* The first prompt didn't say how to check the page offline or on small screens, so I asked the vibe coder to look for gaps and fix the small issues itself before moving on.

---

## Problem 10: Push to GitHub and submit the URL

**Prompt 1**
```
[Problem 10: push the GitHub and submit the URL]

* push my project to a public GitHub repository and submit the repo URL on Canvas
* graders will clone it, so make sure it opens and the files below are there
* include the whole data/ folder (the course data plus my two attack files)
* graders can clone my repo and run my agent DD right away
* do not commit my real .env
   * use .gitignore to keep it out
   * create .gitignore before the first commit, and make sure my API key never appears in any log or output file
   * include .env.example with placeholders only
* before pushing, check that every file in the expected tree exists and is not empty, and show me the result
* put a short note in README.md on how to run my agent DD
* other Python files are fine
* expected repo:

* 

hw6/
├── AI_prompts.md
├── README.md
├── .gitignore
├── .env.example
├── requirements.txt
├── agent.py
├── tools.py
├── models.py
├── prompts/
│   └── prompt.md
├── data/
│   ├── shop_handbook.md
│   ├── prices.json
│   ├── practice_key.json
│   ├── practice_docs/   (the 12 practice documents)
│   ├── exam_docs/       (the 10 exam documents)
│   └── my_attacks/      (my two attack files)
└── output/
    ├── handbook_estimate.md
    ├── harness.md
    ├── usage_log.json
    ├── audit_trail.json
    ├── trap_calls.json
    ├── cache_test.json
    ├── cache_test.md
    ├── attack_results.json
    ├── attack_results.md
    ├── defense_results.json
    ├── defense_results.md
    ├── red_team.md
    ├── exam_results.json
    └── hw6_report.html

*push to GitHub. do what you think is best.
make sure my .env is not uploaded and no file is missing.
give me the repo URL.
```

**Follow-up prompt**
```
I created the empty public repo thdbs902/hw6 on GitHub. Please push.
```

*What was lacking after the first:* My saved GitHub login could push but wasn't allowed to create a new repository, so I created the empty public repo myself and asked the vibe coder to push.
