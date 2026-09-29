# Module knowledge and Empire integration

`cto-legends` is the entry point and only registered skill. `legends-empire`
is the durable Markdown foundation. Vault stewardship is a named maintenance
capability within Empire. Other modules provide specialized capabilities.
Product prominence does not require another installation or skill namespace.

## Name capabilities without splitting packages

Vault stewardship is visibly invoked as a workflow of `legends-empire`.
`legends-vault-stewardship` is a catalog alias for that same installation,
not another distributable module. An ordinary request such as "organize my
vault" should lead the agent to name vault stewardship, load its installed
recipe, check readiness and then perform the authorized work.

Put important capability names and outcomes in catalog purpose/examples, which
appear in the startup index. Signals alone are not visible there. The installed
Markdown recipe owns task-specific announcements and commands. A named alias
resolves the package; it does not insert workflow arguments into `run`.

Create an independent package when its lifecycle and installation need to be
independent. A useful named workflow within an existing module is sufficient
when it shares that module's implementation and updates. Release acceptance
must check both ordinary requests and named invocation, including the actual
installed recipe; homepage presentation alone does not prove discoverability.

## Declare the knowledge shape

A module may ship plain recipes, a reusable reference library, or an
attachable knowledge pack. Choose what the capability actually needs. Do not
manufacture a private mini-vault for every tool. A module with only recipes
should state that clearly.

An attachable pack supplies:

- A versioned identity, owning module, entry point and relative file manifest.
- SHA-256 identities for shipped Markdown references.
- An ontology declaration explaining its role and suggested home.
- Explicit ownership: module references, user work and runtime evidence.
- An update policy that detects user edits before replacing references.
- A preview and a verified attachment path, without another registered skill.

The first implementation is `legends-empire`'s
`knowledge/stewardship/pack.json`, schema `legends.knowledge-pack/v1`.
Its portable shelf is `wiki/library/legends-empire/stewardship`.
See the module's `docs/knowledge-packs.md` for the exact contract and commands.

## Keep meaning in Markdown

Recipes and knowledge remain readable without a database or background
service. JSON is appropriate for machine identities, manifest hashes,
transaction preconditions and comparison evidence. It is supporting state,
not a replacement for a person's project goals, decisions or session handoffs.

Module source lives in the managed installation. A user's vault is a distinct
location. Attachment previews specific writes into that vault and requires an
explicit scoped action. Updates preserve user-owned entry points and work;
modified shipped references produce a conflict for review. Uninstalling a
module does not remove the user's knowledge or attached shelf.

## Release proof

Test a clean installation, recipe handoff, packaged pack loading, attachment,
repeat attachment, an upstream update and a locally edited reference. Verify
that private work survives and that a conflict fails before partial mutation.
State platform limits for both preview and writes. Link into an existing vault
index as a separately reviewed user-content change, never by rewriting it
implicitly during a module install.

Existing module vaults are not automatically migrated or declared compatible.
Adopt this contract module by module when their release is reviewed. The public
Empire tooling and the founder's broader house ontology are related but have
different shipped scope; document that boundary accurately.
