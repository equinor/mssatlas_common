#!/usr/bin/env bash

fail()
{
  echo "$@" >&2
  exit 1
}

[ -n "${GITHUB_REPOSITORY}" ] || fail "No GITHUB_REPOSITORY was supplied."
[ -n "${PULL_REQUEST_LABEL}" ] || fail "No PULL_REQUEST_LABEL was supplied."
[ -n "${GITHUB_TOKEN}" ] || fail "No GITHUB_TOKEN was supplied."

# Determine https://github.com/OWNER/REPO from GITHUB_REPOSITORY.
REPO="${GITHUB_REPOSITORY##*/}"
OWNER="${GITHUB_REPOSITORY%/*}"

# Debugging
echo $OWNER

git config user.name "${GIT_AUTHOR_NAME}"
git config user.email "${GIT_AUTHOR_EMAIL}"

[ -n "${OWNER}" ] || fail "Could not determine GitHub owner from GITHUB_REPOSITORY."
[ -n "${REPO}" ] || fail "Could not determine GitHub repo from GITHUB_REPOSITORY."

# Debugging
OWNER="equinor"
echo $GITHUB_REPOSITORY
echo $OWNER
echo $REPO
echo $PULL_REQUEST_LABEL


echo "Querying Pull Requests:"
# Fetch the SHAs from the pull requests that are marked with $PULL_REQUEST_LABEL.
readarray -t pullrequests < <(
  jq -cn '
    {
      query: $query,
      variables: {
        owner: $owner,
        repo: $repo,
        pull_request_label: $pull_request_label
      }
    }' \
    --arg query '
      query($owner: String!, $repo: String!, $pull_request_label: String!) {
        repository(owner: $owner, name: $repo) {
          pullRequests(states: OPEN, labels: [$pull_request_label], first: 100) {
            nodes {
              mergeable,
              headRefOid
            }
          }
        }
      }' \
    --arg owner "$OWNER" \
    --arg repo "$REPO" \
    --arg pull_request_label "$PULL_REQUEST_LABEL" \
  | curl \
    --fail \
    --show-error \
    --silent \
    --header "Authorization: token $GITHUB_TOKEN" \
    --header "Content-Type: application/json" \
    --data @- \
    https://api.github.com/graphql \
  | jq -r '.data.repository.pullRequests.nodes'
)
echo "${pullrequests[@]}"

echo "Selecting mergeable Pull Requests:"

readarray -t mergeable < <(echo "${pullrequests[@]}" | jq -c '[ .[] | select(.mergeable == "MERGEABLE") ]')

echo "${mergeable[@]}"

readarray -t shas < <(echo "${mergeable[@]}" | jq -r '.[].headRefOid')

echo "Pull requests ready for merge:"

echo "${shas[@]}"
# Do not attempt to merge if there are no pull requests to be merged.
if [ ${#shas[@]} -eq 0 ]
then
  echo "No pull requests with label $PULL_REQUEST_LABEL"
  exit 0
fi

if ! (git merge --no-ff --no-commit "${shas[@]}") then
    echo "Failed to merge pull requests."
    exit 1
else
    echo "Success merging pull requests without fast-forward."
fi

if ! (git commit --message "Merged Pull Requests (${shas[*]})") then
    echo "Failed to commit merge."
    exit 1
else
    echo "Success commit merge."
fi
