/** @odoo-module */
import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { Record, RelationalModel } from "@web/views/basic_relational_model";

/**
 * This model is overridden to allow configuring sale_order_lines through a popup
 * window when a product with 'rent_ok' is selected.
 *
 */
export class LibraryConfiguratorRelationalModel extends RelationalModel {
    setup(params, { action }) {
        super.setup(...arguments);
        this.action = action;
    }
}

LibraryConfiguratorRelationalModel.services = [...RelationalModel.services, "action"];

export class LibraryConfiguratorRecord extends Record {

    _getLibraryInfos() {
        return {
            start_date: this.data.pickup_date,
            return_date: this.data.return_date,
            price_unit: this.data.unit_price,
            product_uom_qty: this.data.quantity,
            is_borrow_order: true,
        };
    }

    /**
     * We let the regular process take place to allow the validation of the required fields
     * to happen.
     *
     * Then we can manually close the window, providing Library information to the caller.
     *
     * @override
     */
    async save() {
        const isSaved = await super.save(...arguments);
        if (!isSaved) {
            return false;
        }
        this.model.action.doAction({
            type: "ir.actions.act_window_close",
            infos: {
                libraryConfiguration: this._getLibraryInfos(),
            },
        });
        return true;
    }
}

LibraryConfiguratorRelationalModel.Record = LibraryConfiguratorRecord;

registry.category("views").add("library_configurator_form", {
    ...formView,
    Model: LibraryConfiguratorRelationalModel,
});
