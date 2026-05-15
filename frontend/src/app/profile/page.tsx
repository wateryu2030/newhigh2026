'use client';

import { useCallback, useEffect, useState } from 'react';
import { useLang } from '@/context/LangContext';
import {
  getUserProfile,
  patchUserProfile,
  postChangePassword,
  getUserQuota,
  type UserProfile,
  type QuotaPayload,
} from '@/api/client';
import { PageSkeleton } from '@/components/PageSkeleton';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';

export default function ProfilePage() {
  const { t } = useLang();
  const router = useRouter();
  const { logout } = useAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [quota, setQuota] = useState<QuotaPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [oldPw, setOldPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [pwMsg, setPwMsg] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState('');
  const [phoneEdit, setPhoneEdit] = useState('');
  const [avatarUrl, setAvatarUrl] = useState('');
  const [profileMsg, setProfileMsg] = useState<string | null>(null);
  const [savingProfile, setSavingProfile] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const [p, q] = await Promise.all([
        getUserProfile().catch(() => null),
        getUserQuota().catch(() => null),
      ]);
      setProfile(p);
      if (p) {
        setDisplayName(p.display_name || '');
        setPhoneEdit(p.phone || '');
        setAvatarUrl(p.avatar_url || '');
      }
      setQuota(q);
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const onChangePw = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwMsg(null);
    try {
      await postChangePassword({ old_password: oldPw, new_password: newPw });
      setPwMsg(t('profile.pwOk'));
      setOldPw('');
      setNewPw('');
    } catch (e) {
      setPwMsg(String(e));
    }
  };

  const onSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setProfileMsg(null);
    setSavingProfile(true);
    try {
      await patchUserProfile({
        display_name: displayName.trim() || null,
        phone: phoneEdit.trim() || null,
        avatar_url: avatarUrl.trim() || null,
      });
      setProfileMsg(t('profile.saved'));
      await load();
    } catch (e) {
      setProfileMsg(String(e));
    } finally {
      setSavingProfile(false);
    }
  };

  if (loading) {
    return (
      <div className="mx-auto max-w-lg space-y-4 px-4 pb-24 pt-6">
        <h1 className="text-xl font-semibold text-on-surface">{t('profile.title')}</h1>
        <PageSkeleton rows={3} />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-lg space-y-6 px-4 pb-24 pt-6">
      <h1 className="text-xl font-semibold text-on-surface">{t('profile.title')}</h1>
      {err ? <p className="text-sm text-amber-400">{err}</p> : null}

      {profile ? (
        <>
          <div className="card space-y-3 border border-card-border p-4 text-sm text-on-surface">
            <p>
              <span className="text-text-secondary">{t('profile.username')}：</span>
              {profile.username}
            </p>
            <p>
              <span className="text-text-secondary">{t('profile.email')}：</span>
              {profile.email}
            </p>
            <p>
              <span className="text-text-secondary">{t('profile.role')}：</span>
              {profile.role}
            </p>
            <p className="text-text-secondary">{t('profile.bindings')}</p>
            <p className="pl-2 text-on-surface">
              {t('profile.wechat')}：{profile.wechat_bound ? t('profile.bound') : t('profile.unbound')} ·{' '}
              {t('profile.feishu')}：{profile.feishu_bound ? t('profile.bound') : t('profile.unbound')}
            </p>
          </div>

          <form onSubmit={(e) => void onSaveProfile(e)} className="card space-y-3 border border-card-border p-4">
            <h2 className="text-sm font-medium text-on-surface">{t('profile.editProfile')}</h2>
            <div>
              <label className="mb-1 block text-xs text-text-secondary">{t('profile.displayName')}</label>
              <input
                className="min-h-touch w-full rounded border border-card-border bg-surface-container-high px-3 py-2 text-sm"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                maxLength={128}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-text-secondary">{t('profile.phone')}</label>
              <input
                className="min-h-touch w-full rounded border border-card-border bg-surface-container-high px-3 py-2 text-sm"
                value={phoneEdit}
                onChange={(e) => setPhoneEdit(e.target.value)}
                autoComplete="tel"
                maxLength={32}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-text-secondary">{t('profile.avatarUrl')}</label>
              <input
                className="min-h-touch w-full rounded border border-card-border bg-surface-container-high px-3 py-2 text-sm"
                value={avatarUrl}
                onChange={(e) => setAvatarUrl(e.target.value)}
                placeholder="https://"
                maxLength={512}
              />
            </div>
            <button
              type="submit"
              disabled={savingProfile}
              className="min-h-touch w-full rounded bg-primary-fixed py-2 text-sm font-medium text-on-warm-fill disabled:opacity-50"
            >
              {savingProfile ? t('common.loading') : t('profile.saveProfile')}
            </button>
            {profileMsg ? <p className="text-xs text-text-secondary">{profileMsg}</p> : null}
          </form>
        </>
      ) : (
        <p className="text-sm text-text-secondary">{t('profile.loginHint')}</p>
      )}

      {quota ? (
        <div className="card space-y-1 border border-card-border p-4 text-sm">
          <p className="font-medium text-on-surface">{t('profile.quota')}</p>
          <p className="text-text-secondary">
            股票问答：{quota.stock_qa.used}/{quota.stock_qa.limit} · 回测：{quota.backtest.used}/
            {quota.backtest.limit}（{quota.day}）
          </p>
        </div>
      ) : null}

      <form onSubmit={(e) => void onChangePw(e)} className="card space-y-3 border border-card-border p-4">
        <h2 className="text-sm font-medium text-on-surface">{t('profile.changePw')}</h2>
        <input
          type="password"
          autoComplete="current-password"
          className="min-h-touch w-full rounded border border-card-border bg-surface-container-high px-3 py-2 text-sm"
          placeholder={t('profile.oldPw')}
          value={oldPw}
          onChange={(e) => setOldPw(e.target.value)}
        />
        <input
          type="password"
          autoComplete="new-password"
          className="min-h-touch w-full rounded border border-card-border bg-surface-container-high px-3 py-2 text-sm"
          placeholder={t('profile.newPw')}
          value={newPw}
          onChange={(e) => setNewPw(e.target.value)}
        />
        <button
          type="submit"
          className="min-h-touch w-full rounded bg-primary-fixed py-2 text-sm font-medium text-on-warm-fill"
        >
          {t('profile.submitPw')}
        </button>
        {pwMsg ? <p className="text-xs text-text-secondary">{pwMsg}</p> : null}
      </form>

      {profile ? (
        <div className="pt-2">
          <button
            type="button"
            onClick={() => {
              logout();
              router.push('/news');
            }}
            className="min-h-touch w-full rounded-lg border border-card-border py-2.5 text-sm text-text-secondary transition hover:bg-surface-container-high"
          >
            {t('auth.logout')}
          </button>
        </div>
      ) : null}
    </div>
  );
}
