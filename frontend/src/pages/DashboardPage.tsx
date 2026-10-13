import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import { usersApi } from '@/api/fetcher'
import type { components } from '@/api/schema'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'

type UserResponse = components['schemas']['UserResponse']

interface FormState {
  name: string
  email: string
}

const INITIAL_FORM: FormState = { name: '', email: '' }

export function DashboardPage() {
  const [users, setUsers] = useState<UserResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [form, setForm] = useState<FormState>(INITIAL_FORM)
  const [submitting, setSubmitting] = useState(false)

  const fetchUsers = useCallback(() =>
    usersApi.list()
      .then(setUsers)
      .catch((e) => toast.error(e instanceof Error ? e.message : '読み込みに失敗しました'))
      .finally(() => setLoading(false)), [])

  useEffect(() => {
    fetchUsers()
  }, [fetchUsers])

  const handleSubmit = useCallback(async () => {
    if (!form.name.trim() || !form.email.trim()) return

    try {
      setSubmitting(true)
      await usersApi.create({ name: form.name.trim(), email: form.email.trim() })
      setDialogOpen(false)
      setForm(INITIAL_FORM)
      toast.success('ユーザーを登録しました')
      await fetchUsers()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : '保存に失敗しました')
    } finally {
      setSubmitting(false)
    }
  }, [form, fetchUsers])

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Users</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            ユーザーの一覧と登録
          </p>
        </div>
        <Button onClick={() => { setForm(INITIAL_FORM); setDialogOpen(true) }}>
          新規登録
        </Button>
      </div>

      {loading ? (
        <div className="rounded-lg border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[60px]">ID</TableHead>
                <TableHead>名前</TableHead>
                <TableHead>メール</TableHead>
                <TableHead className="w-[180px]">作成日時</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {Array.from({ length: 3 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell><Skeleton className="h-5 w-8" /></TableCell>
                  <TableCell><Skeleton className="h-5 w-32" /></TableCell>
                  <TableCell><Skeleton className="h-5 w-48" /></TableCell>
                  <TableCell><Skeleton className="h-5 w-36" /></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : users.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border bg-muted/30 py-16 text-muted-foreground">
          <p className="text-lg font-medium">ユーザーが登録されていません</p>
          <p className="mt-1 text-sm">「新規登録」ボタンからユーザーを追加してください</p>
        </div>
      ) : (
        <div className="rounded-lg border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[60px]">ID</TableHead>
                <TableHead>名前</TableHead>
                <TableHead>メール</TableHead>
                <TableHead className="w-[180px]">作成日時</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((user) => (
                <TableRow key={user.id}>
                  <TableCell className="text-muted-foreground">{user.id}</TableCell>
                  <TableCell className="font-medium">{user.name}</TableCell>
                  <TableCell>{user.email}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {new Date(user.created_at).toLocaleString('ja-JP')}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>ユーザー新規登録</DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="user-name">名前</Label>
              <Input
                id="user-name"
                value={form.name}
                onChange={e => setForm(prev => ({ ...prev, name: e.target.value }))}
                placeholder="名前を入力"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="user-email">メールアドレス</Label>
              <Input
                id="user-email"
                type="email"
                value={form.email}
                onChange={e => setForm(prev => ({ ...prev, email: e.target.value }))}
                placeholder="email@example.com"
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDialogOpen(false)}
              disabled={submitting}
            >
              キャンセル
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={submitting || !form.name.trim() || !form.email.trim()}
            >
              {submitting ? '保存中...' : '登録'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
