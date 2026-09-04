/**
 * SafeRoute - Contacts Module
 */

class ContactsModule {
    constructor(app) {
        this.app = app;
    }

    init() {
        // Modal quick contacts interactions
    }

    openDirect(contactId) {
        const contact = (SAFEROUTE_DATA.emergencyContacts || []).find(c => c.id === contactId);
        if (contact && contact.phoneUrl) {
            window.location.href = contact.phoneUrl;
        }
    }
}

if (typeof window !== "undefined") {
    window.ContactsModule = ContactsModule;
}
