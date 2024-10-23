odoo.define('de_school_library.sale_order_line_wizard', function (require) {
    "use strict";

    var ListRenderer = require('web.ListRenderer');
    var Dialog = require('web.Dialog');

    ListRenderer.include({
        _renderRow: function (record, options) {
            var $row = this._super.apply(this, arguments);

            if (record.model === 'sale.order.line') {
                var productField = $row.find('.o_sol_product_many2one_cell input');
                productField.on('change', this, this._onProductChange.bind(this, record));
            }

            return $row;
        },

        _onProductChange: function (record, ev) {
            var product_id = ev.currentTarget.value;

            if (product_id) {
                // Customize the wizard title and message for your module
                var wizardTitle = "Your Wizard Title";
                var wizardMessage = "Your Wizard Message";

                var dialog = new Dialog(this, {
                    title: wizardTitle,
                    size: 'medium',
                    $content: $('<div>').text(wizardMessage),
                    buttons: [{
                        text: "Ok",
                        classes: 'btn-primary',
                        click: function () {
                            dialog.close();
                        },
                    }, {
                        text: "Cancel",
                        close: true,
                    }],
                });

                dialog.open();
            }
        },
    });
});
