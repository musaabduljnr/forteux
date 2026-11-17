# Design System Consistency Scoring Methodology

**Document Version**: 1.0  
**Phase**: Phase 08 — Design System Extraction & Cross-Screen Consistency  
**Author**: Forteux AI Core Team  

---

## 1. Objective and Principles

The **Design System Consistency Score** measures the degree of visual consistency across a collection of analyzed interface screenshots. It is designed to be:

1. **Mathematically Reproducible**: Computed via an explicit deterministic formula from detected component variations, token deviations, and cross-screen inconsistencies rather than an unexplained LLM guess.
2. **Normalized for Evidence Coverage**: Categories with no observable evidence are not penalized. The denominator dynamically adjusts to evaluated categories only.
3. **Context-Aware**: Intentional variations (destructive buttons, disabled states, error banners, responsive adaptations) are filtered out and do not lower the score.
4. **Transparent & Actionable**: Every point deduction maps directly to an identifiable inconsistency with an explanation and recommended fix.

> [!IMPORTANT]
> The score measures visual consistency within the provided screenshots. It does NOT measure overall product usability, aesthetic taste, accessibility compliance, or business effectiveness.

---

## 2. Category Weights

The score evaluates up to 6 visual categories across screens:

| Category | Identifier | Max Weight ($W_c$) | Scope of Evaluation |
| :--- | :--- | :---: | :--- |
| **Colour Consistency** | `color` | 20% | Consistency of primary, background, surface, text, and border colours across all screens. |
| **Typography Consistency** | `typography` | 20% | Stability of heading hierarchy, body text sizing, label weights, and line-height scale. |
| **Component Consistency** | `components` | 25% | Repeated buttons, text inputs, search bars, tabs, cards, and modal components using identical styles. |
| **Spacing & Layout Rhythm** | `spacing` | 15% | Content padding, section margins, card internal padding, and grid alignment consistency. |
| **Shape & Surface Treatments** | `surfaces` | 10% | Uniformity of border radii, border widths, elevation shadows, and corner curves. |
| **Navigation Consistency** | `navigation` | 10% | Placement, visual treatment, and active states of navigation bars, headers, sidebars, and tab bars. |

$$\sum_{c \in \text{All Categories}} W_c = 100$$

---

## 3. Mathematical Formula

### 3.1 Severity Penalties ($P_i$)
Each detected inconsistency in category $c$ incurs a penalty based on severity:

- **Critical Inconsistency** ($P_{\text{crit}} = 15.0$ pts): Direct visual contradiction that confuses user mental models (e.g. conflicting primary button styles on sibling screens, primary color changing hue arbitrarily).
- **High Inconsistency** ($P_{\text{high}} = 8.0$ pts): Prominent visual mismatch (e.g. mismatched card border radii, inverted heading size hierarchy).
- **Medium Inconsistency** ($P_{\text{med}} = 4.0$ pts): Noticeable polish defect (e.g. input field height variations, secondary button padding discrepancies).
- **Low Inconsistency** ($P_{\text{low}} = 1.5$ pts): Subtle drift (e.g. 1px divider color difference, minor spacing variance in secondary metadata).

### 3.2 Category Score Calculation ($S_c$)
For each evaluated category $c$:

$$D_c = \sum_{i \in \text{Issues}_c} P_i$$

$$S_c = \max\left(0, \; 100 - D_c \times \frac{2}{N_{\text{screens}}}\right)$$

*Where $N_{\text{screens}}$ is the total number of screenshots analyzed ($\ge 2$). Dividing by $N_{\text{screens}}$ normalizes penalties so larger flows with more screens are not artificially penalized merely for having more comparison surfaces.*

### 3.3 Coverage Normalization ($Score_{\text{final}}$)
Let $E \subseteq \text{Categories}$ be the set of categories where sufficient visual evidence was observed in the screenshots:

$$\text{ActiveWeight} = \sum_{c \in E} W_c$$

$$\text{ConsistencyScore} = \frac{\sum_{c \in E} (S_c \times W_c)}{\text{ActiveWeight}}$$

$$\text{ConsistencyScore} = \text{round}(\text{ConsistencyScore}, 1)$$

If a category cannot be evaluated because no applicable components or evidence exist (e.g. a 2-screen journey with no navigation bars), $\text{ActiveWeight}$ excludes that category without penalty.

---

## 4. Extraction Coverage & Confidence

### 4.1 Extraction Coverage ($\text{Cov}$)
$$\text{Cov} = \frac{|E|}{|\text{All Categories}|}$$
Expressed as a percentage (e.g. $\frac{5}{6} = 83.3\%$).

### 4.2 Overall Confidence ($\text{Conf}$)
The weighted average of individual token and component extraction confidences:
$$\text{Conf} = \frac{\sum_{k} \text{conf}_k}{K}$$
Where each $\text{conf}_k \in [0.0, 1.0]$.

---

## 5. Qualitative Score Rating Bands

| Score Range | Tier | Interpretation |
| :---: | :---: | :--- |
| **90.0 – 100.0** | **Exemplary** | High visual uniformity. Components, tokens, and typography adhere closely to an established design system. |
| **75.0 – 89.9** | **Strong** | Consistent visual language with minor localized discrepancies in padding, radius, or secondary styles. |
| **60.0 – 74.9** | **Moderate** | Noticeable design drift. Multiple button variants, inconsistent heading scales, or diverging card treatments across screens. |
| **40.0 – 59.9** | **Fragmented** | Significant divergence across screens. Indicates multiple independent design patterns without a shared token system. |
| **0.0 – 39.9** | **Disjointed** | Screens lack visual continuity. Different font families, conflicting color palettes, and incompatible component libraries. |

---

## 6. Contextual Immunity Rules (Zero-Penalty Variations)

The algorithm explicitly grants immunity to visual differences that serve established UX patterns:

1. **Semantic Color Divergence**: Destructive buttons using red/crimson are recognized as contextual actions, not button color inconsistencies.
2. **Interaction States**: Disabled controls (reduced opacity, grey fill), active navigation tabs (accent underline or pill), and hover/focus indications are exempted.
3. **Modal & Overlay Contexts**: Modal dialogs having darker elevation shadows or tighter padding than base pages are exempted.
4. **Form Validation States**: Error borders, warning callouts, and success checkmarks are recognized as state indicators.
5. **Responsive Adaptations**: Layout reflows (e.g., vertical stack on mobile vs horizontal on desktop) are recognized as intentional responsive behaviors.
