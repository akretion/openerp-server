# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import math

from osv import fields,osv
import tools
import pooler
from tools.translate import _
import logging
import os

class res_payterm(osv.osv):
    _description = 'Payment term'
    _name = 'res.payterm'
    _order = 'name'
    _columns = {
        'name': fields.char('Payment Term (short name)', size=64),
    }
res_payterm()

class res_partner_category(osv.osv):

    def name_get(self, cr, uid, ids, context=None):
        """Return the categories' display name, including their direct
           parent by default.

        :param dict context: the ``partner_category_display`` key can be
                             used to select the short version of the
                             category name (without the direct parent),
                             when set to ``'short'``. The default is
                             the long version.""" 
        if context is None:
            context = {}
        if context.get('partner_category_display') == 'short':
            return super(res_partner_category, self).name_get(cr, uid, ids, context=context)
        reads = self.read(cr, uid, ids, ['name','parent_id'], context=context)
        res = []
        for record in reads:
            name = record['name']
            if record['parent_id']:
                name = record['parent_id'][1]+' / '+name
            res.append((record['id'], name))
        return res

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args=[]
        if not context:
            context={}
        if name:
            # Be sure name_search is symetric to name_get
            name = name.split(' / ')[-1]
            ids = self.search(cr, uid, [('name', operator, name)] + args, limit=limit, context=context)
        else:
            ids = self.search(cr, uid, args, limit=limit, context=context)
        return self.name_get(cr, uid, ids, context)


    def _name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.name_get(cr, uid, ids, context=context)
        return dict(res)

    _description='Partner Categories'
    _name = 'res.partner.category'
    _columns = {
        'name': fields.char('Category Name', required=True, size=64, translate=True),
        'parent_id': fields.many2one('res.partner.category', 'Parent Category', select=True, ondelete='cascade'),
        'complete_name': fields.function(_name_get_fnc, type="char", string='Full Name'),
        'child_ids': fields.one2many('res.partner.category', 'parent_id', 'Child Categories'),
        'active' : fields.boolean('Active', help="The active field allows you to hide the category without removing it."),
        'parent_left' : fields.integer('Left parent', select=True),
        'parent_right' : fields.integer('Right parent', select=True),
        'partner_ids': fields.many2many('res.partner', 'res_partner_category_rel', 'category_id', 'partner_id', 'Partners'),
    }
    _constraints = [
        (osv.osv._check_recursion, 'Error ! You can not create recursive categories.', ['parent_id'])
    ]
    _defaults = {
        'active' : lambda *a: 1,
    }
    _parent_store = True
    _parent_order = 'name'
    _order = 'parent_left'
res_partner_category()

class res_partner_title(osv.osv):
    _name = 'res.partner.title'
    _columns = {
        'name': fields.char('Title', required=True, size=46, translate=True),
        'shortcut': fields.char('Shortcut', required=True, size=16, translate=True),
        'domain': fields.selection([('partner','Partner'),('contact','Contact')], 'Domain', required=True, size=24)
    }
    _order = 'name'
res_partner_title()

def _lang_get(self, cr, uid, context=None):
    obj = self.pool.get('res.lang')
    ids = obj.search(cr, uid, [], context=context)
    res = obj.read(cr, uid, ids, ['code', 'name'], context)
    return [(r['code'], r['name']) for r in res] + [('','')]


class res_partner(osv.osv):
    _description='Partner'
    _name = "res.partner"
    _order = "name"
    _columns = {
        'name': fields.char('Name', size=128, select=True),
        'date': fields.date('Date', select=1),
        'title': fields.many2one('res.partner.title','Title'),
        'parent_id': fields.many2one('res.partner','Parent Partner'),
        'child_ids': fields.one2many('res.partner', 'parent_id', 'Contacts'),
        'ref': fields.char('Reference', size=64, select=1),
        'lang': fields.selection(_lang_get, 'Language', help="If the selected language is loaded in the system, all documents related to this partner will be printed in this language. If not, it will be english."),
        'user_id': fields.many2one('res.users', 'Salesman', help='The internal user that is in charge of communicating with this partner if any.'),
        'vat': fields.char('VAT',size=32 ,help="Value Added Tax number. Check the box if the partner is subjected to the VAT. Used by the VAT legal statement."),
        'bank_ids': fields.one2many('res.partner.bank', 'partner_id', 'Banks'),
        'website': fields.char('Website',size=64, help="Website of Partner."),
        'comment': fields.text('Notes'),
        'address': fields.one2many('res.partner.address', 'partner_id', 'Contacts'), # it should remove in vesion 7 but for now it use for backward compatibility
        'category_id': fields.many2many('res.partner.category', 'res_partner_category_rel', 'partner_id', 'category_id', 'Categories'),
        'events': fields.one2many('res.partner.event', 'partner_id', 'Events'),
        'credit_limit': fields.float(string='Credit Limit'),
        'ean13': fields.char('EAN13', size=13),
        'active': fields.boolean('Active'),
        'customer': fields.boolean('Customer', help="Check this box if the partner is a customer."),
        'supplier': fields.boolean('Supplier', help="Check this box if the partner is a supplier. If it's not checked, purchase people will not see it when encoding a purchase order."),
        'employee': fields.boolean('Employee', help="Check this box if the partner is an Employee."),
        'function': fields.char('Function', size=128),
        'type': fields.selection( [ ('default','Default'),('invoice','Invoice'), ('delivery','Delivery'), ('contact','Contact'), ('other','Other') ],'Address Type', help="Used to select automatically the right address according to the context in sales and purchases documents."),
        'street': fields.char('Street', size=128),
        'street2': fields.char('Street2', size=128),
        'zip': fields.char('Zip', change_default=True, size=24),
        'city': fields.char('City', size=128),
        'state_id': fields.many2one("res.country.state", 'Fed. State', domain="[('country_id','=',country_id)]"),
        'country_id': fields.many2one('res.country', 'Country'),
        'email': fields.char('E-Mail', size=240),
        'phone': fields.char('Phone', size=64),
        'fax': fields.char('Fax', size=64),
        'mobile': fields.char('Mobile', size=64),
        'birthdate': fields.char('Birthdate', size=64),
        'is_company': fields.selection( [ ('contact','Person'),('partner','Company') ],'Contact Type', help="Select if the partner is a company or person"),
        'use_parent_address': fields.boolean('Use Company Address', help="Check to use the company's address"),
        'photo': fields.binary('Photo'),
        'company_id': fields.many2one('res.company', 'Company', select=1),
        'color': fields.integer('Color Index'),
    }
    def _default_category(self, cr, uid, context=None):
        if context is None:
            context = {}
        if 'category_id' in context and context['category_id']:
            return [context['category_id']]
        return []

    def _get_photo(self, cr, uid, is_company, context=None):
        if is_company == 'contact':
            return open(os.path.join( tools.config['root_path'], 'addons', 'base', 'res', 'photo.png'), 'rb') .read().encode('base64')
        return open(os.path.join( tools.config['root_path'], 'addons', 'base', 'res', 'res_company_logo.png'), 'rb') .read().encode('base64')

    _defaults = {
        'active': True,
        'customer': True,
        'category_id': _default_category,
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company')._company_default_get(cr, uid, 'res.partner', context=c),
        'color': 0,
        'is_company': 'contact',
        'type': 'default',
        'use_parent_address':True,
        'photo': _get_photo,
    }

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        name = self.read(cr, uid, [id], ['name'], context)[0]['name']
        default.update({'name': name+ _(' (copy)'), 'events':[]})
        return super(res_partner, self).copy(cr, uid, id, default, context)

    def do_share(self, cr, uid, ids, *args):
        return True
    
    def onchange_type(self, cr, uid, ids, is_company, title, child_ids, photo,context=None):
        photo=False
        if is_company == 'contact':
            return {'value': {'is_company': is_company, 'title': '','child_ids':[(5,)], 'photo': self._get_photo(cr, uid, is_company, context)}}
        elif is_company == 'partner':
            return {'value': {'is_company': is_company, 'title': '','parent_id':False, 'photo': self._get_photo(cr, uid, is_company, context)}}
        return {'value': {'is_comapny': '', 'title': '','photo':''}}
        
    
    def onchange_address(self, cr, uid, ids, use_parent_address, parent_id, context=None):
        if use_parent_address and parent_id:
            parent = self.browse(cr, uid, parent_id, context=context)
            return {'value': {
                'street': parent.street,
                'street2': parent.street2,
                'zip': parent.zip,
                'city': parent.city,
                'state_id': parent.state_id.id,
                'country_id': parent.country_id.id,
                'email': parent.email,
                'phone': parent.phone,
                'fax': parent.fax,
                'mobile': parent.mobile,
                'website': parent.website,
                'ref': parent.ref,
                'lang': parent.lang,
            }}
        return {}

    def _check_ean_key(self, cr, uid, ids, context=None):
        for partner_o in pooler.get_pool(cr.dbname).get('res.partner').read(cr, uid, ids, ['ean13',]):
            thisean=partner_o['ean13']
            if thisean and thisean!='':
                if len(thisean)!=13:
                    return False
                sum=0
                for i in range(12):
                    if not (i % 2):
                        sum+=int(thisean[i])
                    else:
                        sum+=3*int(thisean[i])
                if math.ceil(sum/10.0)*10-sum!=int(thisean[12]):
                    return False
        return True
    
    
    def write(self, cr, uid, ids, vals, context=None):
        # Update the all child and parent_id record 
        update_ids=False
        if isinstance(ids, (int, long)):
            ids = [ids]
        for partner_id in self.browse(cr, uid, ids, context=context):
            is_company=partner_id.is_company
            parent_id=partner_id.parent_id.id 
            if is_company == 'contact' and  parent_id:
                update_ids= self.search(cr, uid, [('parent_id', '=', parent_id),('use_parent_address','=',True)], context=context)
                if parent_id not in update_ids: 
                   update_ids.append(parent_id)
            elif is_company == 'partner':
                 update_ids= self.search(cr, uid, [('parent_id', '=', partner_id.id),('use_parent_address','=',True)], context=context)# 
            if update_ids:
                self.udpate_address(cr,uid,update_ids,False,vals,context)
        return super(res_partner,self).write(cr, uid, ids, vals, context=context)   
    
    def create(self, cr, uid, vals, context=None):
        # temo get the defulat photo image ,it will remove
        if vals.get('parent_id') and vals.get('use_parent_address'):
             update_ids= self.search(cr, uid, [('parent_id', '=', vals.get('parent_id')),('use_parent_address','=',True)], context=context)
             update_ids.append(vals.get('parent_id'))
             self.udpate_address(cr,uid,False,update_ids,vals)
        return super(res_partner,self).create(cr, uid, vals, context=context)     
   
    
    def udpate_address(self,cr,uid,update_ids,parent_id,vals, context=None):
        # Remove this method after testing all case
#        if update_ids:
#            osv.osv.write(self, cr, uid,update_ids, vals,context=context) 
        for key, data in vals.iteritems():
            if key in ('street','street2','zip','city','state_id','country_id','email','phone','fax','mobile','website','ref','lang')  and  data :  
                update_list=update_ids or parent_id
                if update_list :
                    sql = "update res_partner set %(field)s = %%(value)s where id in %%(id)s" % {
                            'field': key,
                        }
                    cr.execute(sql, {
                            'value': data or '',
                            'id':tuple(update_list)
                    })
        return True   
#   _constraints = [(_check_ean_key, 'Error: Invalid ean code', ['ean13'])]

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not len(ids):
            return []
        if context.get('show_ref'):
            rec_name = 'ref'
        else:
            rec_name = 'name'
        reads = self.read(cr, uid, ids, [rec_name,'parent_id'], context=context)
        res = []
        for record in reads:
            name = record['name']
            if record['parent_id']:
                name =name + '(' + record['parent_id'][1] +')'
            res.append((record['id'], name))
        return res

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        # short-circuit ref match when possible
        if name and operator in ('=', 'ilike', '=ilike', 'like'):
            ids = self.search(cr, uid, [('ref', '=', name)] + args, limit=limit, context=context)
            if not ids:
                names=map(lambda i : i.strip(),name.split('('))
                for i in range(len(names)):
                    dom=[('name', operator, names[i])]
                    if i>0:
                        dom+=[('id','child_of',ids)]
                    ids = self.search(cr, uid, dom, limit=limit, context=context)     
                contact_ids = ids
                while contact_ids:
                    contact_ids = self.search(cr, uid, [('parent_id', 'in', contact_ids)], limit=limit, context=context)
                    ids += contact_ids
                if args:
                    ids = self.search(cr, uid, [('id', 'in', ids)] + args, limit=limit, context=context)
            if ids:
                return self.name_get(cr, uid, ids, context)
        return super(res_partner,self).name_search(cr, uid, name, args, operator=operator, context=context, limit=limit)

    def _email_send(self, cr, uid, ids, email_from, subject, body, on_error=None):
        partners = self.browse(cr, uid, ids)
        for partner in partners:
            if partner.email:
                tools.email_send(email_from, [partner.email], subject, body, on_error)
        return True

    def email_send(self, cr, uid, ids, email_from, subject, body, on_error=''):
        while len(ids):
            self.pool.get('ir.cron').create(cr, uid, {
                'name': 'Send Partner Emails',
                'user_id': uid,
#               'nextcall': False,
                'model': 'res.partner',
                'function': '_email_send',
                'args': repr([ids[:16], email_from, subject, body, on_error])
            })
            ids = ids[16:]
        return True

    def address_get(self, cr, uid, ids, adr_pref=None):
        if adr_pref is None:
            adr_pref = ['default']
        # retrieve addresses from the partner itself and its children
        res = []
        # need to fix the ids ,It get  False value in list like ids[False]
        if ids and ids[0]!=False:
            for p in self.browse(cr, uid, ids):
                res.append((p.type, p.id))
                res.extend((c.type, c.id) for c in p.child_ids)
        addr = dict(reversed(res))
        # get the id of the (first) default address if there is one,
        # otherwise get the id of the first address in the list
        if res:
            default_address = addr.get('default', res[0][1])
        else:
            default_address = False
        result = {}
        for a in adr_pref:
            result[a] = addr.get(a, default_address)
        return result

    def gen_next_ref(self, cr, uid, ids):
        if len(ids) != 1:
            return True

        # compute the next number ref
        cr.execute("select ref from res_partner where ref is not null order by char_length(ref) desc, ref desc limit 1")
        res = cr.dictfetchall()
        ref = res and res[0]['ref'] or '0'
        try:
            nextref = int(ref)+1
        except:
            raise osv.except_osv(_('Warning'), _("Couldn't generate the next id because some partners have an alphabetic id !"))

        # update the current partner
        cr.execute("update res_partner set ref=%s where id=%s", (nextref, ids[0]))
        return True

    def view_header_get(self, cr, uid, view_id, view_type, context):
        res = super(res_partner, self).view_header_get(cr, uid, view_id, view_type, context)
        if res: return res
        if (not context.get('category_id', False)):
            return False
        return _('Partners: ')+self.pool.get('res.partner.category').browse(cr, uid, context['category_id'], context).name
    def main_partner(self, cr, uid):
        ''' Return the id of the main partner
        '''
        model_data = self.pool.get('ir.model.data')
        return model_data.browse(
            cr, uid,
            model_data.search(cr, uid, [('module','=','base'),
                                        ('name','=','main_partner')])[0],
            ).res_id
            
    def _display_address(self, cr, uid, address, context=None):
        '''
        The purpose of this function is to build and return an address formatted accordingly to the
        standards of the country where it belongs.

        :param address: browse record of the res.partner.address to format
        :returns: the address formatted in a display that fit its country habits (or the default ones
            if not country is specified)
        :rtype: string
        '''
        # get the address format
        address_format = address.country_id and address.country_id.address_format or \
                                         '%(street)s\n%(street2)s\n%(city)s,%(state_code)s %(zip)s' 
        # get the information that will be injected into the display format
        args = {
            'state_code': address.state_id and address.state_id.code or '',
            'state_name': address.state_id and address.state_id.name or '',
            'country_code': address.country_id and address.country_id.code or '',
            'country_name': address.country_id and address.country_id.name or '',
            'company_name': address.parent_id and address.parent_id.name or '',
        }
        address_field = ['title', 'street', 'street2', 'zip', 'city']
        for field in address_field :
            args[field] = getattr(address, field) or ''

        return address_format % args
        
    def default_get(self, cr, uid, fields, context=None):
        res =  super(res_partner, self).default_get( cr, uid, fields, context)
        if 'is_comapny' in res:
            res.update({'photo': self._get_photo(self, cr, uid, res.get('is_comapny', 'contact'), context)})
        return res

res_partner()

# Deprecated  this feature
class res_partner_address(osv.osv):
    _table = "res_partner"
    _name = 'res.partner.address'
    _order = 'type, name'
    _columns = {
        'partner_id': fields.many2one('res.partner', 'Partner Name', ondelete='set null', select=True, help="Keep empty for a private address, not related to partner."),
        'type': fields.selection( [ ('default','Default'),('invoice','Invoice'), ('delivery','Delivery'), ('contact','Contact'), ('other','Other') ],'Address Type', help="Used to select automatically the right address according to the context in sales and purchases documents."),
        'function': fields.char('Function', size=128),
        'title': fields.many2one('res.partner.title','Title'),
        'name': fields.char('Contact Name', size=64, select=1),
        'street': fields.char('Street', size=128),
        'street2': fields.char('Street2', size=128),
        'zip': fields.char('Zip', change_default=True, size=24),
        'city': fields.char('City', size=128),
        'state_id': fields.many2one("res.country.state", 'Fed. State', domain="[('country_id','=',country_id)]"),
        'country_id': fields.many2one('res.country', 'Country'),
        'email': fields.char('E-Mail', size=240),
        'phone': fields.char('Phone', size=64),
        'fax': fields.char('Fax', size=64),
        'mobile': fields.char('Mobile', size=64),
        'birthdate': fields.char('Birthdate', size=64),
        'is_customer_add': fields.related('partner_id', 'customer', type='boolean', string='Customer'),
        'is_supplier_add': fields.related('partner_id', 'supplier', type='boolean', string='Supplier'),
        'active': fields.boolean('Active', help="Uncheck the active field to hide the contact."),
#        'company_id': fields.related('partner_id','company_id',type='many2one',relation='res.company',string='Company', store=True),
        'company_id': fields.many2one('res.company', 'Company',select=1),
        'color': fields.integer('Color Index'),
    }
    def write(self, cr, uid, ids, vals, context=None):
        logging.getLogger('res.partner').warning("Deprecated, use of res.partner.address and used res.partner")
        return super(res_partner_address,self).write(cr, uid, ids, vals, context=context)   
    def create(self, cr, uid, vals, context=None):
        logging.getLogger('res.partner').warning("Deprecated, use of res.partner.address and used res.partner")
        return super(res_partner_address,self).create(cr, uid, vals, context=context) 
res_partner_address()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
