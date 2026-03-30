export * from '../../../lib/api';
export * from '../../../lib/api/customer';
import { request } from '../../../core/apiClient';

export async function payEmiWallet(loanId: string | number): Promise<{ message: string; wallet_transaction?: object }> {
  return request(`/customer/pay-emi/${loanId}`, { method: 'POST' });
}

