# Self-Directed Counterfactual Reflection (SDCR) — Demo
## The Foundry's Killer Feature in Action

---

## What is SDCR?

**Self-Directed Counterfactual Reflection** is a training paradigm where AI models:
1. Generate alternative scenarios (counterfactuals)
2. Test their own predictions on these scenarios
3. Detect inconsistencies in their reasoning
4. Generate targeted training to fix specific bugs
5. Verify the fix worked

**This doesn't exist anywhere else.**

---

## Demo 1: Mathematical Reasoning

### The Problem
```bash
foundry reflect \
    --question "If a train travels 60km in 30 minutes, how far in 2 hours?" \
    --answer "240km" \
    --explanation "60km in 30 min = 120km per hour. 120 times 2 hours = 240km"
```

### What SDCR Does

**Step 1: Generate Counterfactuals**
```
CF1 (Value Mutation): "If train travels 120km in 30 minutes, how far in 2 hours?"
Expected: 480km (testing if model understands proportionality)

CF2 (Boundary Test): "If train travels 0km in 30 minutes, how far in 2 hours?"
Expected: 0km (testing zero handling)

CF3 (Unit Change): "If train travels 60km in 30 minutes, how far in 30 minutes?"
Expected: 60km (testing same-unit identity)
```

**Step 2: Test Predictions**
If the model answers correctly on all counterfactuals:
```
✓ CF1: Predicted 480km ✓
✓ CF2: Predicted 0km ✓
✓ CF3: Predicted 60km ✓

Consistency Score: 100%
Status: REASONING VERIFIED
```

If the model fails:
```
✓ CF1: Predicted 480km ✓
✗ CF2: Predicted "infinity" ✗ (ERROR: doesn't understand zero)
✓ CF3: Predicted 60km ✓

Consistency Score: 67%
Status: INCONSISTENCY DETECTED
→ Generating targeted training for "zero_boundary_handling"
```

---

## Demo 2: Detecting Pattern-Matching vs Understanding

### The Setup
Model gets this right by pattern-matching:
```
Q: "What is 12 × 8?"
A: "96"
E: "12 times 8 equals 96"
```

### Counterfactual Interrogation
```
CF1: "What is 12 × 0?"
CF2: "What is 0 × 8?"
CF3: "What is 1 × 8?"
```

### If Model is Pattern-Matching
```
✗ CF1: Predicted "12" (pattern: first number)
✗ CF2: Predicted "8" (pattern: second number)
✓ CF3: Predicted "8" (accidentally correct)

INCONSISTENCY: Model doesn't understand multiplication
→ Pattern-matching detected!

REMEDIATION: Generate examples emphasizing:
  - Multiplication as repeated addition
  - Zero property of multiplication
  - Identity property (×1)
```

---

## Demo 3: Code Logic Verification

### The Code
```python
def calculate_discount(price, discount_percent):
    return price - (price * discount_percent / 100)
```

### Model's Explanation
"This function calculates the discounted price by subtracting the discount amount from the original price."

### Counterfactual Tests
```
CF1: What if discount_percent is 0?
     Expected: return price
     
CF2: What if discount_percent is 100?
     Expected: return 0
     
CF3: What if price is negative?
     Expected: [depends on business logic]
     
CF4: What if discount_percent is negative?
     Expected: [increase price or error]
```

### Bug Detection
If model says CF4 "should decrease price" but code actually increases it:
```
INCONSISTENCY: Explanation contradicts code behavior
→ Model doesn't understand negative discount logic

REMEDIATION: Generate example with explicit negative handling
```

---

## Demo 4: Logical Consistency

### The Problem
```
Statement 1: "All birds can fly"
Statement 2: "Penguins are birds"
Statement 3: "Penguins cannot fly"

Model says: "Statements 1 and 2 are true, 3 is false"
```

### Consistency Check
```
Transitivity Test:
  If All birds can fly (S1)
  AND Penguins are birds (S2)
  THEN Penguins can fly (derived)
  
  But model says Penguins cannot fly (S3)
  
CONTRADICTION DETECTED!

REMEDIATION: Generate examples about:
  - Universal vs existential quantifiers
  - Exception handling in logic
  - Transitive property verification
```

---

## How It Works (Technical)

### The SDCR Loop
```python
class ReflectionEngine:
    def reflect(self, question, answer, explanation):
        # 1. Generate counterfactuals
        counterfactuals = cf_engine.generate(
            question, answer, explanation
        )
        
        # 2. Test predictions
        predictions = [
            model.predict(cf.question) 
            for cf in counterfactuals
        ]
        
        # 3. Check consistency
        report = consistency_checker.check(
            predictions, expected_answers
        )
        
        # 4. If inconsistent, remediate
        if not report.is_consistent:
            training_examples = generate_targeted_examples(
                report.violations
            )
            model.micro_train(training_examples)
        
        # 5. Verify fix
        return verify_consistency(question)
```

### Counterfactual Strategies
1. **Value Mutation** — Change numbers while preserving structure
2. **Constraint Inversion** — Flip min/max, before/after
3. **Boundary Testing** — Zero, infinity, edge cases
4. **Unit Transformation** — Miles→km, hours→minutes
5. **Premise Removal** — Remove key information
6. **Order Permutation** — Change sequence

### Consistency Checks
- Numerical consistency (within tolerance)
- Transitive consistency (A→B→C implies A→C)
- Monotonic relationships
- Dimensional analysis
- Boundary conditions

---

## Why This Changes Everything

### Before SDCR
```
Traditional Training:
  Train on static dataset → Deploy → Find failures → Collect feedback 
  → Retrain → Deploy → Find new failures...
  
Problems:
  - Failures found post-deployment
  - Human feedback is expensive
  - No understanding of WHY failures occur
  - Black box models
```

### With SDCR
```
SDCR Training:
  Train → Self-test → Find bugs → Self-correct → Verify → Deploy
  
Advantages:
  - Failures found during training
  - Self-directed, no human needed
  - Understands WHY failures occur
  - Causally-grounded models
```

---

## The Vision

> **"Training wheels for AI reasoning"**

Current AI is like a student who memorizes answers.
SDCR creates a student who:
- Checks their work
- Identifies what they don't understand
- Studies exactly that
- Verifies they've learned it

**This is how you build AI systems that are robust, trustworthy, and actually understand what they're doing.**

---

## Next Steps

1. **Try it yourself:**
   ```bash
   foundry reflect --question "..." --answer "..." --explanation "..."
   ```

2. **Read the paper:** *"Self-Directed Counterfactual Reflection: A New Paradigm for Robust AI Reasoning"* (In submission to ICLR 2026)

3. **Join the research:** Contribute new counterfactual strategies and consistency checks

---

## The Bottom Line

**OpenAI scales compute. The Foundry scales understanding.**

This is the feature that makes The Foundry legendary.
