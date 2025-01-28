# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

{
    'name' : 'Microsoft Azure SSO Integration',

    "author": "Softhealer Technologies",

    "license": "OPL-1",

    "website": "https://www.softhealer.com",

    "support": "support@softhealer.com",

    "version": "0.0.1",

    "category": "Extra Tools",

    "summary": "Odoo SSO Odoo Login With Microsoft SSo Microsoft Office365 SSo Microsoft Office 365 SSo Office 365 Microsoft Office365 Microsoft Microsoft Azure OAuth2 SSO Integration Microsoft OAuth2 SSO Integration Sync Microsoft Users to Odoo Sync Microsoft User to Odoo OAuth Single Sign On SSO Single Sign On into Odoo OAuth SSO Login plugin Odoo Single Sign-On With OAuth OpenID Connect plugin Azure AD Azure B2C Office 365 Cognito Ping Keycloak WHMCS Okta OpenID Connect provider Single Sign On SSO Odoo Integration Odoo SSO Integration Microsoft Azure SSO Odoo Login Integration Microsoft Azure SSO Odoo Log in Integration Microsoft Azure SSO Integration with Odoo Login with Microsoft Azure Microsoft Azure Login Microsoft Azure Log in Microsoft Azure Log-in Microsoft Azure Integration with Odoo Integration Signin with Microsoft Account azure sso azure ad sso microsoft sso active directory sso with azure single signon sso in active directory microsoft azure sso azure ad saml azure saml office 365 sso azure identity provider azure ad oidc saml active directory azure ad sso saml Microsoft Azure SSO Integration Odoo on Azure Odoo Microsoft SSO Odoo Microsoft Azure Integration Odoo SSO Microsoft Odoo Azure Portal Odoo Office 365 Calendar Integration Odoo Integration With Microsoft Users Login Using Microsoft Account Odoo Integration Module Microsoft Azure Office 365 Odoo Microsoft Account Microsoft Azure Single Sign on",

    "description": """By using the Microsoft Azure SSO Integration module, You can login in the Odoo with Microsoft account credentials. No more counting of usernames and passwords just a click and there you are in Odoo!""",
    'depends' : ['base_setup','auth_oauth'],
    'data' : [
        'views/oauth_provider_views.xml',
        'data/microsoft_oauth_data.xml',
    ],
    'demo' : [],
    'installation': True,
    'application' : True,
    'auto_install' : False,
    "images": ["static/description/background.png", ],
    'external_dependencies': {'python': ['simplejson', 'pyjwt']},
    "price": "90",
    "currency": "EUR"
}
