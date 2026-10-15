import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Toaster } from '@/components/ui/sonner'
import { TabLayout } from '@/layouts/TabLayout'
import { AnalyticsPage } from '@/pages/AnalyticsPage'
import { ExerciseDetailPage } from '@/pages/ExerciseDetailPage'
import { ExerciseEditPage } from '@/pages/ExerciseEditPage'
import { ExercisePickerPage } from '@/pages/ExercisePickerPage'
import { ExercisesPage } from '@/pages/ExercisesPage'
import { ExportPage } from '@/pages/ExportPage'
import { HomePage } from '@/pages/HomePage'
import { PastProgramsPage } from '@/pages/PastProgramsPage'
import { ProgramCreatePage } from '@/pages/ProgramCreatePage'
import { ProgramPage } from '@/pages/ProgramPage'
import { ProgramPreviewPage } from '@/pages/ProgramPreviewPage'
import { ProgramRulesPage } from '@/pages/ProgramRulesPage'
import { TrainingLogPage } from '@/pages/TrainingLogPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<TabLayout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/program" element={<ProgramPage />} />
          <Route path="/program/new" element={<ProgramCreatePage />} />
          <Route path="/program/rules" element={<ProgramRulesPage />} />
          <Route path="/program/preview" element={<ProgramPreviewPage />} />
          <Route path="/program/past" element={<PastProgramsPage />} />
          <Route path="/exercises" element={<ExercisesPage />} />
          <Route path="/exercises/new" element={<ExerciseEditPage />} />
          <Route path="/exercises/:uid" element={<ExerciseDetailPage />} />
          <Route path="/exercises/:uid/edit" element={<ExerciseEditPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/export" element={<ExportPage />} />
        </Route>
        <Route path="/training-logs/:uid" element={<TrainingLogPage />} />
        <Route path="/training-logs/:uid/exercise-picker" element={<ExercisePickerPage />} />
      </Routes>
      <Toaster />
    </BrowserRouter>
  )
}

export default App
