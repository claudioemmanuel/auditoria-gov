#!/usr/bin/env bash
# =============================================================================
# setup_project_board.sh — Create OpenWatch Scrumban board on GitHub Projects v2
#
# Prerequisites:
#   - gh CLI authenticated with a token that has the 'project' scope:
#       gh auth login   (select all scopes including 'project')
#   - Set GITHUB_USER env var or pass as argument:
#       GITHUB_USER=claudioemmanuel bash tools/setup_project_board.sh
#
# Usage:
#   bash tools/setup_project_board.sh [github-username-or-org]
# =============================================================================

set -euo pipefail

OWNER="${1:-${GITHUB_USER:-claudioemmanuel}}"
PROJECT_TITLE="OpenWatch Development Board"

echo "==> Creating project board for owner: $OWNER"

# ── Step 1: Get owner node ID ─────────────────────────────────────────────────
OWNER_ID=$(gh api graphql \
  -f query='query($login:String!){user(login:$login){id}}' \
  -f login="$OWNER" \
  --jq '.data.user.id')

echo "    Owner ID: $OWNER_ID"

# ── Step 2: Create the project ────────────────────────────────────────────────
PROJECT_DATA=$(gh api graphql \
  -f query='mutation($ownerId:ID!,$title:String!){createProjectV2(input:{ownerId:$ownerId,title:$title}){projectV2{id number url}}}' \
  -f ownerId="$OWNER_ID" \
  -f title="$PROJECT_TITLE")

PROJECT_ID=$(echo "$PROJECT_DATA" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data']['createProjectV2']['projectV2']['id'])")
PROJECT_NUMBER=$(echo "$PROJECT_DATA" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data']['createProjectV2']['projectV2']['number'])")
PROJECT_URL=$(echo "$PROJECT_DATA" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data']['createProjectV2']['projectV2']['url'])")

echo "    Project ID:     $PROJECT_ID"
echo "    Project Number: $PROJECT_NUMBER"
echo "    Project URL:    $PROJECT_URL"

# ── Step 3: Get the default Status field and set its options ──────────────────
echo "==> Fetching default Status field..."

STATUS_FIELD=$(gh api graphql \
  -f query='query($owner:String!,$number:Int!){user(login:$owner){projectV2(number:$number){fields(first:20){nodes{... on ProjectV2SingleSelectField{id name options{id name}}}}}}}' \
  -f owner="$OWNER" \
  -F number="$PROJECT_NUMBER")

STATUS_FIELD_ID=$(echo "$STATUS_FIELD" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for node in d['data']['user']['projectV2']['fields']['nodes']:
    if node.get('name') == 'Status':
        print(node['id'])
        break
")
echo "    Status field ID: $STATUS_FIELD_ID"

# ── Step 4: Add Priority single-select field ──────────────────────────────────
echo "==> Adding Priority field..."
gh api graphql \
  -f query='mutation($pid:ID!,$name:String!,$opts:[ProjectV2SingleSelectFieldOptionInput!]!){addProjectV2Field(input:{projectId:$pid,dataType:SINGLE_SELECT,name:$name,singleSelectOptions:$opts}){field{... on ProjectV2SingleSelectField{id name}}}}' \
  -f pid="$PROJECT_ID" \
  -f name="Priority" \
  -f opts='[{"name":"High","color":RED,"description":"Must be addressed immediately"},{"name":"Medium","color":YELLOW,"description":"Address in current sprint"},{"name":"Low","color":GREEN,"description":"Nice to have"}]' \
  --jq '.data.addProjectV2Field.field.name' \
  && echo "    Priority field created"

# ── Step 5: Add Type single-select field ─────────────────────────────────────
echo "==> Adding Type field..."
gh api graphql \
  -f query='mutation($pid:ID!,$name:String!,$opts:[ProjectV2SingleSelectFieldOptionInput!]!){addProjectV2Field(input:{projectId:$pid,dataType:SINGLE_SELECT,name:$name,singleSelectOptions:$opts}){field{... on ProjectV2SingleSelectField{id name}}}}' \
  -f pid="$PROJECT_ID" \
  -f name="Type" \
  -f opts='[{"name":"Feature","color":BLUE,"description":"New functionality"},{"name":"Bug","color":RED,"description":"Something broken"},{"name":"Refactor","color":PURPLE,"description":"Code improvement"},{"name":"Docs","color":GRAY,"description":"Documentation"},{"name":"Chore","color":GRAY,"description":"Maintenance"}]' \
  --jq '.data.addProjectV2Field.field.name' \
  && echo "    Type field created"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  ✅  OpenWatch Development Board created successfully        ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  URL: $PROJECT_URL"
echo "║                                                              ║"
echo "║  Next steps (manual in GitHub UI):                          ║"
echo "║  1. Rename default Status options to match Scrumban:         ║"
echo "║     • Todo → Backlog                                         ║"
echo "║     • In Progress → In Progress                              ║"
echo "║     • Done → Done                                            ║"
echo "║     • Add: Ready for Analysis, In Review                     ║"
echo "║  2. Enable automations:                                      ║"
echo "║     • Issues opened → Backlog                                ║"
echo "║     • PR opened → In Review                                  ║"
echo "║     • PR merged → Done (close issue)                         ║"
echo "║  3. Link repo: Settings → Manage access → Add repository     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
