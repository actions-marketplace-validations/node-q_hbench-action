# Releasing

For maintainers.

1. Merge the change to `main` and let `Test` pass on it.
2. Tag the release and move the major tag to it:

   ```bash
   git tag -a v1.0.1 -m v1.0.1 && git push origin v1.0.1
   git tag -f v1 v1.0.1 && git push -f origin v1
   ```

3. Create the GitHub release from the tag, with the changes since the last one:

   ```bash
   gh release create v1.0.1 --repo node-q/hbench-action --generate-notes
   ```

   To list a release in GitHub Marketplace, edit it on GitHub and tick **Publish this Action to the GitHub
   Marketplace**. The first time, a maintainer accepts the Marketplace developer agreement; `action.yml` must
   stay at the repository's root, with its `name` unique in the Marketplace.

A change that breaks a workflow using `@v1` (a renamed or removed input or output, a changed default) is a new
major version, `v2`, and `v1` stays where it is.
