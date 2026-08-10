import { useState, useCallback } from 'react';

/**
 * Reusable custom React hook to standardize state management across CRUD pages
 * (Departments, Roles, Users, Modules, Companies, Elections).
 */
export function useCrudState(initialPageSize = 10) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState('');
  
  // Search & Filter state
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('active');

  // Pagination state
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);

  // Modal controls
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  
  // Single-step Delete confirmation modal target
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const openCreateModal = useCallback(() => {
    setEditingItem(null);
    setError(null);
    setIsModalOpen(true);
  }, []);

  const openEditModal = useCallback((item) => {
    setEditingItem(item);
    setError(null);
    setIsModalOpen(true);
  }, []);

  const closeModal = useCallback(() => {
    setIsModalOpen(false);
    setEditingItem(null);
    setError(null);
  }, []);

  const openDeleteModal = useCallback((item) => {
    setDeleteTarget(item);
    setError(null);
  }, []);

  const closeDeleteModal = useCallback(() => {
    setDeleteTarget(null);
    setIsDeleting(false);
  }, []);

  const clearMessages = useCallback(() => {
    setError(null);
    setSuccessMsg('');
  }, []);

  return {
    data,
    setData,
    loading,
    setLoading,
    error,
    setError,
    successMsg,
    setSuccessMsg,
    searchTerm,
    setSearchTerm,
    statusFilter,
    setStatusFilter,
    page,
    setPage,
    totalPages,
    setTotalPages,
    totalItems,
    setTotalItems,
    isModalOpen,
    openCreateModal,
    openEditModal,
    closeModal,
    editingItem,
    deleteTarget,
    openDeleteModal,
    closeDeleteModal,
    isDeleting,
    setIsDeleting,
    clearMessages
  };
}

export default useCrudState;
