# Automatic display names during Entra registration

Status: required tenant configuration, not enabled by the demo client. The
workspace has no connected Entra administration session or registration-service
checkout. The host-browser change is independent of this configuration.

The requested behavior is to derive a missing display name from the submitted
first and last names during registration. Keep an existing meaningful display
name, including one an administrator has corrected manually. This rule does not
perform a directory-wide backfill or continuously rename existing accounts.

## Registration contract

Configure a Microsoft-hosted external-tenant user flow to collect `givenName`,
`surname` and `displayName`. Its authenticated registration API must handle
`OnAttributeCollectionSubmit` before the new account is saved:

1. Read the submitted built-in string attributes from
   `data.userSignUpInfo.attributes`.
2. If `displayName` is present and its trimmed value is neither empty nor
   `unknown` (case-insensitive), continue without changing it.
3. Otherwise, trim the first and last names and join their nonempty values with
   one space. Preserve Unicode, punctuation and the spelling inside each name.
4. If neither name has a value, return a field validation error. Do not invent
   a name or save another `unknown` value.
5. Return the derived value using this action, with `Ada Lovelace` replaced by
   the computed name:

```json
{
  "data": {
    "@odata.type": "microsoft.graph.onAttributeCollectionSubmitResponseData",
    "actions": [
      {
        "@odata.type": "microsoft.graph.attributeCollectionSubmit.modifyAttributeValues",
        "attributes": {"displayName": "Ada Lovelace"}
      }
    ]
  }
}
```

Entra ignores response attributes outside the configured attribute collection.
Do not remove `displayName` from the user flow to hide its input. Microsoft
Graph exposes a `hidden` input setting; verify that the selected flow still
delivers the attribute and accepts the generated value before hiding the field.
The registration API must validate the extension's authenticated caller and
expected tenant/application before processing an event. Follow the existing
identity service's deployment and authentication controls. The desktop client
does not need Graph write permissions or an application secret for this rule.

## Acceptance before enabling

Exercise a new registration through the actual hosted user flow. Confirm the
saved directory field and a fresh account-picker session show the derived name.
Also cover surrounding whitespace, Unicode names, one supplied name, both names
missing, a meaningful manually entered display name, and a display-name
attribute missing from the event. A missing configured attribute must be treated
as a deployment/configuration failure, rather than reported as successful
automatic naming. Do not log registration payloads or identity tokens.

The existing manually corrected profile does not need another write. Applying
this change requires the owning registration API and Entra user-flow access;
merely updating or rebuilding this repository does not enable the tenant rule.

## Microsoft references

- [Attribute collection submit event and response contract](https://learn.microsoft.com/en-us/entra/identity-platform/custom-extension-onattributecollectionsubmit-retrieve-return-data)
- [Configure authenticated custom extensions](https://learn.microsoft.com/en-us/entra/identity-platform/custom-extension-attribute-collection)
- [User-flow input configuration, including hidden fields](https://learn.microsoft.com/en-us/graph/api/resources/authenticationattributecollectioninputconfiguration?view=graph-rest-1.0)
