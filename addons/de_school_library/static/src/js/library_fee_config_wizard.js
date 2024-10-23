odoo.define('de_school_library.library_fee_config_wizard', function (require) {
    "use strict";

    var core = require('web.core');
    var _t = core._t;
    var Dialog = require('web.Dialog');
    var rpc = require('web.rpc');
    var ListRenderer = require('web.ListRenderer'); // Import the ListRenderer

    ListRenderer.include({
        _renderRow: function (record, options) {
            var $row = this._super.apply(this, arguments);

            // Check if the record is a sale order line
            if (record.model === 'sale.order.line') {
                var productField = $row.find('.o_sol_product_many2one input');
                productField.on('change', this, this._onProductChange.bind(this, record));
            }

            return $row;
        },

        _onProductChange: function (record, ev) {
            var product_id = ev.currentTarget.value;

            if (product_id) {
                // Customize the wizard title and message
                var wizardTitle = _t("Your Wizard Title");
                var wizardMessage = _t("Your Wizard Message");

                var dialog = new Dialog(this, {
                    title: wizardTitle,
                    size: 'medium', // You can adjust the size as needed
                    $content: $('<div>').text(wizardMessage),
                    buttons: [{
                        text: _t("Ok"),
                        classes: 'btn-primary',
                        click: function () {
                            dialog.close();
                        },
                    }, {
                        text: _t("Cancel"),
                        close: true,
                    }],
                });

                dialog.open();
            }
        },
    });
});
