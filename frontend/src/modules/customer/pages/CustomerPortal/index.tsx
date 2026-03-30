import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { useNavigate } from "react-router-dom";
import type { LoanType } from "../CustomerDashboard";
import EmiPanel from "./components/EmiPanel";
import DashboardTab from "./components/DashboardTab";
import DocumentsTab from "./components/DocumentsTab";
import NotificationsTab from "./components/NotificationsTab";
import SupportTab from "./components/SupportTab";
import WalletTab from "./components/WalletTab";
import LoansTab from "./components/LoansTab";
import TrackTab from "./components/TrackTab";
import ProfileTab from "./components/ProfileTab";
import type { CustomerNotification } from "./components/CustomerNotifications";
import { payEmiWallet } from '../../../../modules/customer/services/customerApi';

import type { SupportTicket } from "./components/CustomerSupport";
import {
  buildTimeline,
  mergeTransactions,
  normalizeKycStatus,
  tabs,
  type LoanRecord,
  type RecentActivityItem,
  type TabKey,
  txnKind,
  txnTitle,
} from "./utils";
import {
  customerCreateSupportTicket,
  customerListSupportTickets,
  getCustomerEmiDetails,
  getCustomerNotifications,
  getCustomerLoanOffers,
  getCustomerProfile,
  getMPINStatus,
  getSession,
  getWalletBalance,
  listCustomerLoans,
  // listTransactions,
  getTransactionHistory,
  forecloseLoan,
  setSession,
  verifyMPIN,
  startHybridEmiPayment,
  uploadSignedSanctionLetter,
  customerSanctionLetterUrl,
} from '../../../../modules/customer/services/customerApi';
import type { CustomerLoanOffer } from '../../../../modules/customer/services/customerApi';
import MPINVerificationModal from "../../../../components/MPINVerificationModal";
import AddMoneyModal from "../../../../components/AddMoneyModal";
import WalletToast, { walletToastKeyframes, walletCenterKeyframes } from "../../../../components/WalletToast";
import CashfreePaymentOverlay from "../../../../components/CashfreePaymentOverlay";
import ChangeMPINModal from "../../../../components/ChangeMPINModal";
import SettlementPreviewModal from "../../../../components/SettlementPreviewModal";
import DataState from "../../../../components/ui/DataState";
import useLocalNotifications from "./hooks/useLocalNotifications";
import useCashfreeOrderConfirmation, { type WalletToastState } from "./hooks/useCashfreeOrderConfirmation";
import { downloadEmiStatementCsv, downloadTransactionsCsv } from "./csv";
import { downloadSanctionLetter } from "./sanctionLetter";
import { downloadNocLetter } from "./nocLetter";
import "../../styles/customer-portal.css";
import "../../styles/loan-application.css";

export default function CustomerPortal() {
  const WALLET_TOAST_RESTORE_KEY = "wallet_toast_restore";
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabKey>("dashboard");
  const [selectedLoanType, setSelectedLoanType] = useState<LoanType | null>(null);
  const [loanEntryMode, setLoanEntryMode] = useState<"apply" | "calculator">("apply");
  const [loanOffers, setLoanOffers] = useState<Partial<Record<LoanType, CustomerLoanOffer>>>({});
  const [customerEmail, setCustomerEmail] = useState("");
  const [customerName, setCustomerName] = useState("Customer");
  const [accountNumber, setAccountNumber] = useState("");
  const [ifsc, setIfsc] = useState("");
  const [balance, setBalance] = useState<number>(0);
  const [cibilScore, setCibilScore] = useState<number | null>(null);
  const [walletBalanceOverride, setWalletBalanceOverride] = useState<null | {
    value: number;
    mode: "credit" | "debit";
    expiresAt: number;
  }>(null);
  const [kycStatus, setKycStatus] = useState("Pending");
  const [latestApplication, setLatestApplication] = useState<LoanRecord | undefined>(undefined);
  const [loanList, setLoanList] = useState<LoanRecord[]>([]);
  const [emiDetails, setEmiDetails] = useState<Awaited<ReturnType<typeof getCustomerEmiDetails>> | null>(null);
  const [emiDetailsLoading, setEmiDetailsLoading] = useState(false);
  const [recentActivity, setRecentActivity] = useState<RecentActivityItem[]>([]);
  const [txPage, setTxPage] = useState<number>(1);
  const [txPageSize, setTxPageSize] = useState<number>(10);
  const [txTotal, setTxTotal] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<any | null>(null);
  const [mpinSet, setMpinSet] = useState(true);
  const [showMpinForWallet, setShowMpinForWallet] = useState(false);
  const [walletMoneyModalMode, setWalletMoneyModalMode] = useState<"credit" | "debit" | null>(null);
  const [showChangeMpin, setShowChangeMpin] = useState(false);
  const [showMpinForEmi, setShowMpinForEmi] = useState(false);
  const [showSettlementPreview, setShowSettlementPreview] = useState(false);
  const [showMpinForForeclose, setShowMpinForForeclose] = useState(false);
  const [showForecloseConfirm, setShowForecloseConfirm] = useState(false);
  const [forecloseBusy, setForecloseBusy] = useState(false);

  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [ticketsLoading, setTicketsLoading] = useState(false);
  const [ticketCreateLoading, setTicketCreateLoading] = useState(false);

  const location = useLocation();

  const errorMessage = useMemo(() => {
    if (!error) return null;
    if (typeof error === "string") return error;
    if (typeof (error as any)?.humanMessage === "string") return (error as any).humanMessage as string;
    if (typeof (error as any)?.message === "string") return (error as any).message as string;
    try {
      return JSON.stringify(error);
    } catch {
      return String(error);
    }
  }, [error]);

  const storageKeyBase = useMemo(() => {
    const session = getSession();
    const id = String(session?.userId || "customer");
    return `paycrest_customer_${id}`;
  }, []);

  const { notifications, setNotifications, loadNotifications, saveNotifications, pushNotification } =
    useLocalNotifications(storageKeyBase);

  const applyBalance = (candidate: number | null | undefined) => {
    const next = Number(candidate);
    if (!Number.isFinite(next)) return;

    setBalance((current) => {
      const override = walletBalanceOverride;
      if (!override) return next;
      if (override.expiresAt <= Date.now()) {
        setWalletBalanceOverride(null);
        return next;
      }

      // If backend balance is lagging behind a recent wallet action, keep optimistic value until it catches up.
      if (override.mode === "credit") {
        if (next < override.value) return Math.max(current, override.value);
        setWalletBalanceOverride(null);
        return next;
      }
      // debit
      if (next > override.value) return Math.min(current, override.value);
      setWalletBalanceOverride(null);
      return next;
    });
  };

  const refreshSupportTickets = async () => {
    setTicketsLoading(true);
    try {
      const rows = await customerListSupportTickets();
      setTickets(Array.isArray(rows) ? rows : []);
    } catch {
      setTickets([]);
    } finally {
      setTicketsLoading(false);
    }
  };

  useEffect(() => {
    const p = location.pathname || "";
    if (p.includes("/customer/wallet")) setActiveTab("wallet");
    else if (p.includes("/customer/emi")) setActiveTab("emi");
    else if (p.includes("/customer/loans")) setActiveTab("loans");
    else if (p.includes("/customer/track")) setActiveTab("track");
    else if (p.includes("/customer/documents")) setActiveTab("documents");
    else if (p.includes("/customer/notifications")) setActiveTab("notifications");
    else if (p.includes("/customer/support")) setActiveTab("support");
    else if (p.includes("/customer/profile")) setActiveTab("profile");
    else setActiveTab("dashboard");
  }, [location.pathname]);

  useEffect(() => {
    void refreshSupportTickets();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const refreshEmiDetails = async (loanId: number) => {
    setEmiDetailsLoading(true);
    try {
      const details = await getCustomerEmiDetails(loanId);
      setEmiDetails(details || null);
    } catch {
      setEmiDetails(null);
    } finally {
      setEmiDetailsLoading(false);
    }
  };

  const refreshCustomer = async () => {
    const session = getSession();
    if (!session || session.role !== "customer") {
      navigate("/login/customer");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const profile = await getCustomerProfile();
      setCustomerEmail(profile.email || "");
      setCustomerName(profile.name || "Customer");
      setAccountNumber(String(profile.account_number || ""));
      setIfsc(profile.ifsc || "");
      try {
        const wallet = await getWalletBalance();
        applyBalance(wallet?.balance || 0);
      } catch {
        // Keep last known wallet balance on transient wallet API failures.
      }
      setKycStatus(normalizeKycStatus(profile.kyc_status));
      setCibilScore(typeof profile.cibil_score === "number" ? profile.cibil_score : null);
      try {
        const offersRes = await getCustomerLoanOffers();
        if (offersRes?.offers) setLoanOffers(offersRes.offers);
      } catch {
        setLoanOffers({});
      }

      let loans: any[] = [];
      try {
        const res = await listCustomerLoans();
        loans = Array.isArray(res) ? (res as any[]) : [];
      } catch (err) {
        const status = (err as any)?.status;
        const msg =
          err instanceof Error
            ? ((err as any).humanMessage || err.message || "")
            : String(err ?? "");
        // Some backends respond 404 when the customer has no loans yet.
        if (status === 404 || /loan not found/i.test(msg)) {
          loans = [];
        } else {
          throw err;
        }
      }

      setLoanList(loans as LoanRecord[]);
      const sorted = loans
        .slice()
        .sort((a, b) =>
          String((a as any)?.applied_at || "").localeCompare(String((b as any)?.applied_at || "")),
        );
      setLatestApplication(sorted.length ? (sorted[sorted.length - 1] as LoanRecord) : undefined);

      // Dashboard always needs the most recent transactions (page 1), even if user paged in Wallet.
      const txPageToFetch = activeTab === "dashboard" ? 1 : txPage || 1;
      const txLimitToFetch = txPageSize || 10;
      const txns = await getTransactionHistory(txPageToFetch, txLimitToFetch);
      // if API returns array, assume small list; otherwise support { items, total }
      if (Array.isArray(txns)) {
        setRecentActivity((prev) => mergeTransactions(txns as any[], prev as any[]));
        setTxTotal((txns as any[]).length);
        if (activeTab !== "dashboard") setTxPage(txPageToFetch);
      } else if ((txns as any).items) {
        setRecentActivity((prev) => mergeTransactions(((txns as any).items || []) as any[], prev as any[]));
        setTxTotal((txns as any).total || 0);
        if (activeTab !== "dashboard") {
          setTxPage((txns as any).page || txPageToFetch);
          setTxPageSize((txns as any).page_size || txLimitToFetch);
        }
      } else {
        setRecentActivity(Array.isArray(txns) ? txns : []);
      }

      let serverNotifications: Array<{
        _id: string;
        title: string;
        message: string;
        kind?: "info" | "success" | "warning" | "error";
        created_at: string;
        read?: boolean;
      }> = [];
      try {
        const notes = await getCustomerNotifications(100);
        serverNotifications = Array.isArray(notes) ? notes : [];
      } catch {
        serverNotifications = [];
      }

      // In-app notifications (stored locally per user)
      try {
        const nowIso = new Date().toISOString();
        const snapKey = `${storageKeyBase}_snapshot_v1`;
        const prevRaw = localStorage.getItem(snapKey);
        const prev = prevRaw ? (JSON.parse(prevRaw) as any) : null;

        const current = {
          kyc_status: String(profile.kyc_status || ""),
          latest_loan_status: String(sorted.length ? (sorted[sorted.length - 1] as any)?.status || "" : ""),
          latest_loan_id: sorted.length ? (sorted[sorted.length - 1] as any)?.loan_id : null,
          last_txn_id: Array.isArray(txns) ? (txns[0] as any)?.id : (txns as any)?.items?.[0]?.id,
        };

        localStorage.setItem(snapKey, JSON.stringify(current));

        let next = loadNotifications();
        if (serverNotifications.length) {
          const mapped: CustomerNotification[] = serverNotifications.map((n) => ({
            id: String(n._id),
            title: n.title,
            message: n.message,
            kind: n.kind || "info",
            created_at: n.created_at,
            read: Boolean(n.read),
          }));
          const byId = new Map<string, CustomerNotification>();
          [...mapped, ...next].forEach((n) => byId.set(String(n.id), n));
          next = Array.from(byId.values()).sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
        }

        if (!prev) {
          next = [
            {
              id: `welcome-${Date.now()}`,
              title: "Welcome to PayCrest",
              message: "Your account is ready. Complete KYC to unlock all services.",
              created_at: nowIso,
              read: false,
              kind: "info",
            },
            ...next,
          ];
        }

        if (prev && String(prev.kyc_status || "") !== String(current.kyc_status || "")) {
          const label = normalizeKycStatus(current.kyc_status);
          next = [
            {
              id: `kyc-${Date.now()}`,
              title: "KYC Update",
              message: `Your KYC status changed to: ${label}.`,
              created_at: nowIso,
              read: false,
              kind: label === "Approved" ? "success" : label === "Rejected" ? "error" : "info",
            },
            ...next,
          ];
        }

        if (
          prev &&
          String(prev.latest_loan_status || "") !== String(current.latest_loan_status || "") &&
          current.latest_loan_id
        ) {
          next = [
            {
              id: `loan-${Date.now()}`,
              title: "Loan Status Update",
              message: `Loan #${current.latest_loan_id} status: ${String(current.latest_loan_status || "").replace(/_/g, " ")}.`,
              created_at: nowIso,
              read: false,
              kind: "info",
            },
            ...next,
          ];
        }

        if (prev && prev.last_txn_id && current.last_txn_id && String(prev.last_txn_id) !== String(current.last_txn_id)) {
          const latestTxn = Array.isArray(txns) ? (txns[0] as any) : (txns as any)?.items?.[0];
          const title = txnTitle(latestTxn?.type);
          const kind = txnKind(latestTxn?.type, latestTxn?.amount);
          const amt = Number(latestTxn?.amount ?? 0);
          const absAmt = Math.abs(amt);
          const loanTag = latestTxn?.loan_id ? `Loan #${latestTxn.loan_id}` : "Account";
          const amountLabel = Number.isFinite(absAmt) ? `INR ${absAmt.toLocaleString("en-IN")}` : "INR -";
          const messageClean = `${title} - ${loanTag} - ${amountLabel}`;
          const txnCreatedAt = String(latestTxn?.created_at || nowIso);

          next = [
            {
              id: `txn-${Date.now()}`,
              title: "Wallet Activity",
              message: messageClean,
              created_at: txnCreatedAt,
              read: false,
              kind: kind === "credit" ? "success" : kind === "debit" ? "warning" : "info",
            },
            ...next,
          ];
        }

        next = next.slice(0, 100);
        saveNotifications(next);
        setNotifications(next);
      } catch {
        // ignore notification errors
      }

      try {
        const supportRows = await customerListSupportTickets();
        setTickets(Array.isArray(supportRows) ? supportRows : []);
      } catch {
        // keep existing ticket list if refresh fails
      }
    } catch (err) {
      const msg =
        err instanceof Error
          ? ((err as any).humanMessage || err.message || "Failed to load profile")
          : "Failed to load profile";
      setError(String(msg));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refreshCustomer();
    // Check if MPIN is set up
    const session = getSession();
    setMpinSet(session?.mpinSet ?? true);
    if (session?.role === "customer") {
      void (async () => {
        try {
          const status = await getMPINStatus();
          const mpinSetValue = !!status?.mpin_set;
          setMpinSet(mpinSetValue);
          setSession({ ...session, mpinSet: mpinSetValue });
        } catch {
          // ignore: keep existing mpinSet value
        }
      })();
    }
  }, []);

  const loadTxPage = async (page: number, limit = txPageSize) => {
    try {
      const res = await getTransactionHistory(page, limit);
      if (Array.isArray(res)) {
        setRecentActivity((prev) => mergeTransactions(res as any[], prev as any[]));
        setTxTotal((res as any[]).length);
        setTxPage(page);
        setTxPageSize(limit);
      } else if ((res as any).items) {
        setRecentActivity((prev) => mergeTransactions(((res as any).items || []) as any[], prev as any[]));
        setTxTotal((res as any).total || 0);
        setTxPage((res as any).page || page);
        setTxPageSize((res as any).page_size || limit);
      }
    } catch (err) {
      // ignore transaction load errors here
    }
  };

  useEffect(() => {
    if (activeTab !== "emi") return;
    if (!latestApplication?.loan_id) {
      setEmiDetails(null);
      return;
    }
    void refreshEmiDetails(latestApplication.loan_id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, latestApplication?.loan_id]);

  useEffect(() => {
    if (activeTab !== "track") return;
    setError(null);
    void refreshCustomer();
    const id = window.setInterval(() => {
      void refreshCustomer();
    }, 15000);
    return () => window.clearInterval(id);
  }, [activeTab]);

  useEffect(() => {
    if (activeTab !== "dashboard") return;
    void refreshCustomer();
    const id = window.setInterval(() => {
      void refreshCustomer();
    }, 30000);
    return () => window.clearInterval(id);
  }, [activeTab]);

  useEffect(() => {
    if (activeTab !== "wallet") return;

    const refreshWallet = async () => {
      try {
        // Keep wallet available balance consistent with backend source of truth.
        const wallet = await getWalletBalance();
        applyBalance(wallet?.balance || 0);
      } catch {
        // ignore wallet refresh failures
      }

      // keep transaction list fresh (especially for loan disbursement credits)
      if ((txPage || 1) === 1) void loadTxPage(1, txPageSize || 10);
    };

    void refreshWallet();
    const id = window.setInterval(() => {
      void refreshWallet();
    }, 15000);
    return () => window.clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, txPageSize, txPage]);

  const kycApproved = kycStatus.toLowerCase() === "approved";
  const kycState =
    kycStatus.toLowerCase() === "approved"
      ? "verified"
      : kycStatus.toLowerCase().includes("verification")
        ? "submitted"
        : "pending";
  const kycActionAvailable = kycState === "pending";
  const unreadCount = useMemo(() => notifications.filter((n) => !n.read).length, [notifications]);
  const activeLoanCount = useMemo(() => {
    const activeStatuses = new Set([
      "applied",
      "assigned_to_verification",
      "verification_done",
      "manager_approved",
      "pending_admin_approval",
      "admin_approved",
      "sanction_sent",
      "signed_received",
      "active",
      "disbursed",
    ]);
    return loanList.filter((l) =>
      l.status && activeStatuses.has(String(l.status).toLowerCase()),
    ).length;
  }, [loanList]);
  const hasActiveLoan = activeLoanCount > 0;

  const timelineItems = useMemo(() => buildTimeline(latestApplication), [latestApplication]);

  const minWalletBalanceRequired = useMemo(() => {
    const sanctionedStatuses = new Set([
      "admin_approved",
      "sanction_sent",
      "signed_received",
      "ready_for_disbursement",
      "active",
      "completed",
      "disbursed",
    ]);
    const hasSanctionedLoan = loanList.some((l) =>
      sanctionedStatuses.has(String(l?.status || "").toLowerCase()),
    );
    return hasSanctionedLoan ? 1500 : 0;
  }, [loanList]);

  const handleAddMoney = async () => {
    setError(null);
    setWalletMoneyModalMode("credit");
  };

  const handleDebitMoney = async () => {
    setError(null);
    const current = Number(balance || 0);
    if (minWalletBalanceRequired > 0 && current <= minWalletBalanceRequired) {
      setError(`You must maintain a minimum balance of Rs ${minWalletBalanceRequired.toLocaleString("en-IN")} after sanction. Debit is not allowed at this balance.`);
      return;
    }
    setWalletMoneyModalMode("debit");
  };

  const [walletToast, setWalletToast] = useState<WalletToastState>({ visible: false, amount: 0, context: "wallet" });
  const [cashfreeOverlay, setCashfreeOverlay] = useState<"idle" | "loading" | "success">("idle");
  const walletPopupEnabled = true;
  const walletToastAnimationsEnabled = true;
  const cashfreeOverlayEnabled = false;
  const showWalletToast = useCallback(
    (next: WalletToastState) => {
      setWalletToast(next);
      try {
        if (next?.visible) {
          sessionStorage.setItem(
            WALLET_TOAST_RESTORE_KEY,
            JSON.stringify({ ...next, createdAt: Date.now() }),
          );
        } else {
          sessionStorage.removeItem(WALLET_TOAST_RESTORE_KEY);
        }
      } catch {
        // ignore
      }
    },
    [WALLET_TOAST_RESTORE_KEY],
  );

  useCashfreeOrderConfirmation({
    locationSearch: location.search,
    locationPathname: location.pathname,
    navigate,
    txPageSize,
    refreshCustomer,
    loadTxPage,
    pushNotification,
    setError: (msg: string) => setError(msg),
    setWalletToast: showWalletToast,
    setCashfreeOverlay,
  });

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(WALLET_TOAST_RESTORE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as WalletToastState & { createdAt?: number };
      const createdAt = Number(parsed?.createdAt || 0);
      const ageMs = Date.now() - (Number.isFinite(createdAt) ? createdAt : 0);
      if (ageMs >= 0 && ageMs <= 120_000 && parsed?.visible) {
        showWalletToast({
          visible: true,
          amount: Number(parsed?.amount || 0),
          mode: parsed?.mode,
          context: parsed?.context || "wallet",
        });
      }
      sessionStorage.removeItem(WALLET_TOAST_RESTORE_KEY);
    } catch {
      // ignore
    }
  }, [location.key]);

  const handlePayEmi = async () => {
    // Show M-PIN verification modal before performing EMI payment
    if (!latestApplication?.loan_id) return;
    setShowMpinForEmi(true);
  };

  const handleDownloadEmiStatement = () => {
    setError(null);
    if (!latestApplication?.loan_id) {
      setError("No loan found to generate a statement");
      return;
    }
    if (emiDetailsLoading) {
      setError("Please wait until EMI details are loaded");
      return;
    }
    if (!emiDetails) {
      setError("Open the EMI tab to load your schedule, then try again");
      return;
    }
    try {
      downloadEmiStatementCsv(customerName, latestApplication.loan_id, emiDetails);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate EMI statement");
    }
  };

  const exportTxCsv = () => {
    try {
      downloadTransactionsCsv(recentActivity, txPage);
    } catch {
      // ignore
    }
  };

  const handleLoanSubmit = async () => {
    await refreshCustomer();
  };

  const showTopTabs = true;

  return (
    <div className="portal-shell">
      <main className="portal-main">
        <section className="portal-view portal-view--dashboard" style={{ marginBottom: 14 }}>
          {showTopTabs && (
            <nav className="portal-tabs portal-tabs--top" aria-label="Customer dashboard tabs">
              {tabs.map((tab) => (
                <button
                  key={tab.key}
                  type="button"
                  className={`portal-tab ${activeTab === tab.key ? "active" : ""} ${
                    tab.key === "wallet" && !mpinSet ? "disabled" : ""
                  }`}
                  disabled={tab.key === "wallet" && !mpinSet}
                  title={
                    tab.key === "wallet" && !mpinSet
                      ? "Please set up your M-PIN first"
                      : ""
                  }
                  onClick={() => {
                    setError(null);
                    if (tab.key === "wallet" && !mpinSet) {
                      return;
                    }
                    if (tab.key === "loans") {
                      setSelectedLoanType(null);
                      setLoanEntryMode("apply");
                    }
                    setActiveTab(tab.key);
                  }}
                >
                  {tab.key === "notifications" && unreadCount > 0 ? `${tab.label} (${unreadCount})` : tab.label}
                </button>
              ))}
            </nav>
          )}
        </section>

        {activeTab === "dashboard" && kycState !== "verified" ? (
          <section className="portal-kyc-notice-row" aria-label="KYC status notice">
            <div className="bankdash-kyc-banner" role="status" aria-live="polite">
              <div>
                <strong>{kycState === "submitted" ? "KYC Submitted" : "One-time action required"}</strong>
                <p>
                  {kycState === "submitted"
                    ? "Your KYC is under verification. You will be notified once approved."
                    : "Complete KYC verification to unlock all services."}
                </p>
              </div>
              <button
                type="button"
                className={`bankdash-btn-primary ${!kycActionAvailable ? "bankdash-btn-disabled" : ""}`}
                onClick={kycActionAvailable ? () => navigate("/kyc") : undefined}
                disabled={!kycActionAvailable}
                aria-disabled={!kycActionAvailable}
              >
                {kycState === "submitted" ? "KYC Submitted" : "Complete KYC"}
              </button>
            </div>
          </section>
        ) : null}

        <section className="portal-status-row" aria-label="Status messages">
          {errorMessage ? (
            <div className="portal-status-row__error">
              <DataState
                variant="error"
                title="We couldn't load your data"
                message={errorMessage}
                ctaLabel="Retry"
                onCta={() => {
                  void refreshCustomer();
                }}
                secondaryCtaLabel="Contact Support"
                onSecondaryCta={() => setActiveTab("support")}
              />
            </div>
          ) : null}
          {loading ? (
            <DataState variant="loading" title="Loading dashboard" message="Fetching wallet, loan, and EMI details securely." />
          ) : null}
        </section>
        {false && (
          <div
            style={{
              padding: "12px 16px",
              backgroundColor: "#fef3c7",
              border: "1px solid #fcd34d",
              borderRadius: "6px",
              color: "#92400e",
              fontSize: "14px",
              marginBottom: "16px",
            }}
          >
            ⚠️ <strong>Action Required:</strong> Please set up your M-PIN to access wallet features and complete transactions.{" "}
            <button
              onClick={() => navigate("/mpin-setup")}
              style={{
                background: "transparent",
                border: "none",
                color: "#2563eb",
                cursor: "pointer",
                textDecoration: "underline",
                fontWeight: "600",
                padding: 0,
              }}
            >
              Set up M-PIN now
            </button>
          </div>
        )}

        {activeTab === "dashboard" && (
          <DashboardTab
            customerName={customerName}
            accountNumber={accountNumber}
            ifsc={ifsc}
            kycApproved={kycApproved}
            kycStatus={kycStatus}
            balance={balance}
            activeLoanCount={activeLoanCount}
            latestApplication={latestApplication}
            emiDetails={emiDetails}
            recentActivity={recentActivity}
            onViewSettlement={() => {
              if (!hasActiveLoan) return;
              setShowSettlementPreview(true);
            }}
            onForeclose={() => {
              if (!hasActiveLoan) return;
              setShowMpinForForeclose(true);
            }}
            onOpenDocuments={() => setActiveTab("documents")}
            onOpenSupport={() => setActiveTab("support")}
            onKycClick={() => navigate("/kyc")}
            onOpenWallet={() => setShowMpinForWallet(true)}
            onOpenLoans={() => setActiveTab("loans")}
            onOpenTrack={() => setActiveTab("track")}
            onOpenEmi={() => setActiveTab("emi")}
          />
        )}

        {activeTab === "documents" && (
          <DocumentsTab
            kycStatus={kycStatus}
            latestApplication={latestApplication}
            recentActivity={recentActivity}
            onOpenKyc={() => navigate("/kyc")}
            onOpenTrack={() => setActiveTab("track")}
            onOpenSupport={() => setActiveTab("support")}
            onDownloadSanction={() => {
              if (!latestApplication?.loan_id) return;
              void (async () => {
                setError(null);
                try {
                  await downloadSanctionLetter(latestApplication.loan_id);
                } catch (err) {
                  setError(err instanceof Error ? err.message : String(err || "Failed to download sanction letter"));
                }
              })();
            }}
            onDownloadNoc={() => {
              if (!latestApplication?.loan_id) return;
              void (async () => {
                setError(null);
                try {
                  await downloadNocLetter(latestApplication.loan_id);
                } catch (err) {
                  setError(err instanceof Error ? err.message : String(err || "Failed to download NOC letter"));
                }
              })();
            }}
            onExportTxCsv={exportTxCsv}
          />
        )}

        {activeTab === "notifications" && (
          <NotificationsTab
            items={notifications}
            onMarkAllRead={() => {
              const next = notifications.map((n) => ({ ...n, read: true }));
              setNotifications(next);
              saveNotifications(next);
            }}
            onClearAll={() => {
              setNotifications([]);
              saveNotifications([]);
            }}
            onMarkRead={(id) => {
              const next = notifications.map((n) => (n.id === id ? { ...n, read: true } : n));
              setNotifications(next);
              saveNotifications(next);
            }}
          />
        )}

        {activeTab === "support" && (
          <SupportTab
            tickets={tickets}
            loading={ticketsLoading}
            creating={ticketCreateLoading}
            onRefresh={() => {
              void refreshSupportTickets();
            }}
            onCreate={async (t) => {
              setTicketCreateLoading(true);
              try {
                const created = await customerCreateSupportTicket({
                  category: t.category,
                  subject: t.subject,
                  message: t.message,
                  attachment: t.attachment || null,
                });
                setTickets((prev) => [created, ...(prev || [])]);
                const n: CustomerNotification[] = [
                  {
                    id: `ticket-${Date.now()}`,
                    title: "Support Ticket Created",
                    message: `Ticket ${created.ticket_id} submitted: ${created.subject}`,
                    created_at: new Date().toISOString(),
                    read: false,
                    kind: "success" as const,
                  },
                  ...(notifications || []),
                ].slice(0, 100);
                setNotifications(n);
                saveNotifications(n);
              } catch (err) {
                setError(err instanceof Error ? err.message : String(err || "Failed to create support ticket"));
              } finally {
                setTicketCreateLoading(false);
              }
            }}
          />
        )}

        {activeTab === "wallet" && (
          <WalletTab
            accountNumber={accountNumber}
            ifsc={ifsc || "PCIN01001"}
            balance={balance}
            recentActivity={recentActivity}
            onAddMoney={handleAddMoney}
            onDebitMoney={handleDebitMoney}
            page={txPage}
            pageSize={txPageSize}
            total={txTotal}
            onPageChange={(p) => void loadTxPage(p, txPageSize)}
            onPageSizeChange={(s) => void loadTxPage(1, s)}
          />
        )}

        {showMpinForWallet && (
          <MPINVerificationModal
            onVerified={() => {
              setShowMpinForWallet(false);
              setActiveTab("wallet");
            }}
            onCancel={() => setShowMpinForWallet(false)}
          />
        )}

        {walletMoneyModalMode && (
          <AddMoneyModal
            mode={walletMoneyModalMode}
            availableBalance={balance}
            minRequiredBalance={minWalletBalanceRequired}
            onClose={() => setWalletMoneyModalMode(null)}
            onSuccess={async (newBal, delta, mode) => {
              const prev = Number(balance || 0);
              setWalletMoneyModalMode(null);
              // update balance immediately for live feedback
              const raw = Number(newBal);
              const optimistic = mode === "credit" ? prev + Math.abs(delta || 0) : Math.max(0, prev - Math.abs(delta || 0));
              let nb = Number.isFinite(raw) ? raw : optimistic;
              if (mode === "credit" && nb <= prev) nb = optimistic;
              if (mode === "debit" && nb >= prev) nb = optimistic;
              setWalletBalanceOverride({ value: nb, mode, expiresAt: Date.now() + 2 * 60 * 1000 });
              applyBalance(nb);

              // prepend synthetic transaction so history shows update immediately
              try {
                const txn = {
                  id: `local-${Date.now()}`,
                  loan_id: undefined,
                  loan_type: undefined,
                  type: mode === "debit" ? "debit" : "credit",
                  amount: mode === "debit" ? -Math.abs(delta) : Math.abs(delta),
                  balance_after: nb,
                  created_at: new Date().toISOString(),
                } as any;
                setRecentActivity((prevList) => [txn, ...(prevList || []).slice(0, Math.max(0, (txPageSize || 5) - 1))]);
                setTxTotal((t) => (typeof t === "number" ? t + 1 : 1));
              } catch {}

              // show toast for credit or debit
              if (mode === "credit") {
                const credited = Math.max(0, nb - prev, delta || 0);
                if (credited > 0) showWalletToast({ visible: true, amount: credited, mode: "credit", context: "wallet" });
                pushNotification({
                  title: "Wallet Credited",
                  message: `Credited INR ${Math.abs(delta || 0).toLocaleString("en-IN")} to your wallet.`,
                  kind: "success",
                });
              } else {
                const debited = delta || Math.max(0, prev - nb);
                showWalletToast({ visible: true, amount: debited, mode: "debit", context: "wallet" });
                pushNotification({
                  title: "Wallet Debited",
                  message: `Debited INR ${Math.abs(delta || 0).toLocaleString("en-IN")} from your wallet.`,
                  kind: "warning",
                });
              }

              // refresh full profile in background
              void refreshCustomer();
              // and refresh wallet txns shortly (backend may append txn async)
              window.setTimeout(() => {
                void loadTxPage(1, txPageSize || 10);
              }, 500);
            }}
          />
        )}

        {walletPopupEnabled && walletToast.visible && (
          <>
            {walletToastAnimationsEnabled ? <style>{walletCenterKeyframes + "\n" + walletToastKeyframes}</style> : null}
            <WalletToast
              amount={walletToast.amount}
              mode={walletToast.mode}
              context={walletToast.context}
              onClose={() => showWalletToast({ visible: false, amount: 0, mode: undefined, context: "wallet" })}
            />
          </>
        )}
        {cashfreeOverlayEnabled && cashfreeOverlay !== "idle" && (
          <CashfreePaymentOverlay
            variant={cashfreeOverlay === "loading" ? "loading" : "success"}
            title={cashfreeOverlay === "loading" ? "Processing payment" : "Successful amount credited"}
            subtitle={cashfreeOverlay === "loading" ? "Moving to Cashfree secure checkout..." : "Amount credited to wallet."}
            onClose={() => setCashfreeOverlay("idle")}
          />
        )}

        {activeTab === "emi" && (
          <section className="portal-view portal-view--emi">
            <EmiPanel
              latestApplication={latestApplication}
              emiDetails={emiDetails}
              emiDetailsLoading={emiDetailsLoading}
              kycApproved={kycApproved}
              kycStatus={kycStatus}
              cibilScore={cibilScore}
              customerName={customerName}
              onPayEmi={handlePayEmi}
              onDownloadStatement={handleDownloadEmiStatement}
              onOpenSettlement={() => setShowSettlementPreview(true)}
            />
          </section>
        )}
        {activeTab === "loans" && (
          <LoansTab
            kycApproved={kycApproved}
            hasActiveLoan={hasActiveLoan}
            loanOffers={loanOffers}
            selectedLoanType={selectedLoanType}
            loanEntryMode={loanEntryMode}
            onApplyLoan={(loanType) => {
              setLoanEntryMode("apply");
              setSelectedLoanType(loanType);
            }}
            onEmiOpen={(loanType) => {
              setLoanEntryMode("calculator");
              setSelectedLoanType(loanType);
            }}
            onBackToOffers={() => {
              setSelectedLoanType(null);
              setLoanEntryMode("apply");
            }}
            onProceedToApply={(loanType) => {
              setSelectedLoanType(loanType);
              setLoanEntryMode("apply");
            }}
            onSubmitted={handleLoanSubmit}
          />
        )}
        {activeTab === "track" && (
          <TrackTab
            items={timelineItems}
            sanctionLetter={{
              isAvailable: ["admin_approved", "sanction_sent", "signed_received", "ready_for_disbursement", "active", "completed", "disbursed"].includes(
                String(latestApplication?.status || "").toLowerCase(),
              ),
              fileName: latestApplication?.loan_id ? `sanction_letter_${latestApplication.loan_id}.pdf` : "sanction_letter.pdf",
              issuedOn: latestApplication?.approved_at ? new Date(latestApplication.approved_at).toLocaleDateString() : undefined,
              referenceId: latestApplication?.loan_id ? `SAN-${latestApplication.loan_id}` : "SAN-CURRENT",
              fileUrl: latestApplication?.loan_id ? customerSanctionLetterUrl(latestApplication.loan_id) : undefined,
              fileMimeType: "application/pdf",
              onDownload: () => {
                void (async () => {
                  setError(null);
                  if (!latestApplication?.loan_id) {
                    setError("No loan selected");
                    return;
                  }
                  try {
                    await downloadSanctionLetter(latestApplication.loan_id);
                  } catch (err) {
                    setError(err instanceof Error ? err.message : String(err || "Failed to download sanction letter"));
                  }
                })();
              },
              canUpload: String(latestApplication?.status || "").toLowerCase() === "sanction_sent",
              onUpload: async (file: File) => {
                setError(null);
                if (!latestApplication?.loan_id) throw new Error("No loan selected");
                try {
                  await uploadSignedSanctionLetter(latestApplication.loan_id, file);
                  await refreshCustomer();
                } catch (err) {
                  throw err;
                }
              },
            }}
          />
        )}
        {activeTab === "profile" && (
          <ProfileTab
            email={customerEmail}
            name={customerName}
            kycStatus={kycStatus}
            cibilScore={cibilScore}
            latestApplication={latestApplication}
            onChangeMpin={() => setShowChangeMpin(true)}
          />
        )}

        {showChangeMpin && (
          <ChangeMPINModal
            email={customerEmail}
            onClose={() => setShowChangeMpin(false)}
            onSuccess={() => {
              setShowChangeMpin(false);
            }}
          />
        )}
        {showMpinForEmi && (
          <MPINVerificationModal
            onVerified={async (mpin) => {
              setShowMpinForEmi(false);
              setError(null);
              try {
                await verifyMPIN(mpin);
                if (!latestApplication?.loan_id) {
                  setError("No loan selected for EMI payment");
                  return;
                }

                const start = await startHybridEmiPayment(latestApplication.loan_id, mpin);

                if (start?.paid) {
                  const paidAmt = Number(start?.amount || 0);
                  if (Number.isFinite(paidAmt) && paidAmt > 0) {
                    showWalletToast({ visible: true, amount: paidAmt, mode: "debit", context: "emi" });
                  }
                  pushNotification({
                    title: "EMI Paid",
                    message: "EMI paid from wallet successfully.",
                    kind: "success",
                  });
                  void refreshCustomer();
                  void refreshEmiDetails(latestApplication.loan_id);
                  return;
                }

                const orderId = String((start as any)?.order_id || "");
                const paymentLink = (start as any)?.payment_link as string | undefined | null;
                const paymentSessionId = (start as any)?.payment_session_id as string | undefined | null;
                const emiAmt = Number((start as any)?.emi_amount || 0);

                if (!orderId) throw new Error("Cashfree order creation failed (missing order_id)");
                try {
                  const session = getSession();
                  sessionStorage.setItem(
                    "cashfree_pending",
                    JSON.stringify({
                      orderId,
                      purpose: "wallet_topup_then_emi",
                      amount: emiAmt,
                      createdAt: Date.now(),
                      userId: String(session?.userId || ""),
                    }),
                  );
                } catch {}

                if (paymentLink) {
                  window.location.assign(paymentLink);
                  return;
                }
                if (paymentSessionId) {
                  const { openCashfreeCheckout } = await import("../../../../lib/cashfree");
                  await openCashfreeCheckout({ paymentSessionId, redirectTarget: "_self" });
                  return;
                }

                throw new Error("Cashfree order created but no payment link/session was returned");
              } catch (err) {
                setError(err instanceof Error ? err : new Error("EMI payment failed"));
              }
            }}
            onCancel={() => setShowMpinForEmi(false)}
          />
        )}
        {showMpinForForeclose && (
          <MPINVerificationModal
            onVerified={async (mpin) => {
              setShowMpinForForeclose(false);
              setError(null);
              try {
                await verifyMPIN(mpin);
                if (!latestApplication?.loan_id) {
                  setError("No loan selected for foreclosure");
                  return;
                }
                if (!hasActiveLoan) {
                  setError("No active loan available for foreclosure");
                  return;
                }
                setShowForecloseConfirm(true);
              } catch (err) {
                setError(err instanceof Error ? err : new Error("Foreclosure failed"));
              }
            }}
            onCancel={() => setShowMpinForForeclose(false)}
          />
        )}
        {showForecloseConfirm ? (
          <div className="portal-confirm-backdrop" role="dialog" aria-modal="true" aria-label="Confirm foreclosure">
            <div className="portal-confirm-card">
              <h3>Confirm Foreclosure</h3>
              <p>Foreclose this loan now? Foreclosure may include charges.</p>
              <div className="portal-confirm-actions">
                <button
                  type="button"
                  className="portal-confirm-btn secondary"
                  onClick={() => {
                    if (forecloseBusy) return;
                    setShowForecloseConfirm(false);
                  }}
                  disabled={forecloseBusy}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="portal-confirm-btn primary"
                  onClick={async () => {
                    if (!latestApplication?.loan_id) {
                      setError("No loan selected for foreclosure");
                      return;
                    }
                    setForecloseBusy(true);
                    setError(null);
                    try {
                      await forecloseLoan(latestApplication.loan_id);
                      await refreshCustomer();
                      const next: CustomerNotification[] = [
                        {
                          id: `foreclose-${Date.now()}`,
                          title: "Foreclosure Requested",
                          message: "Your foreclosure request was submitted.",
                          created_at: new Date().toISOString(),
                          read: false,
                          kind: "info" as const,
                        },
                        ...(notifications || []),
                      ].slice(0, 100);
                      setNotifications(next);
                      saveNotifications(next);
                      setShowForecloseConfirm(false);
                    } catch (err) {
                      setError(err instanceof Error ? err : new Error("Foreclosure failed"));
                    } finally {
                      setForecloseBusy(false);
                    }
                  }}
                  disabled={forecloseBusy}
                >
                  {forecloseBusy ? "Processing..." : "Confirm Foreclose"}
                </button>
              </div>
            </div>
          </div>
        ) : null}
        {showSettlementPreview && latestApplication?.loan_id && (
          <SettlementPreviewModal
            loanId={latestApplication.loan_id}
            onClose={() => setShowSettlementPreview(false)}
            onSuccess={async () => {
              await refreshCustomer();
              if (latestApplication?.loan_id) await refreshEmiDetails(latestApplication.loan_id);
            }}
          />
        )}
      </main>
    </div>
  );
}





